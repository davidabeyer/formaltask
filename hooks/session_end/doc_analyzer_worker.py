#!/usr/bin/env python3
"""Doc Analyzer Worker - Background Documentation Analysis

Implements <!-- BACKGROUND-WORKERS --> pattern from README.md.

This worker runs as a detached background process after session end to:
1. Analyze git commits from the session
2. Use GPT-5.1 + instructor for structured analysis
3. Generate documentation update suggestions
4. Write to .claude/doc-guard/pending.json

Spawned by: session_end.py wrapper (fire-and-forget pattern)
Input: Hook data via stdin (session_id, start_time)
Logging: ~/.claude/doc-guard/worker.log

Exit Codes:
- 0: Success (even if API key missing - graceful degradation)
- 1: Critical error (invalid input)
"""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import logging
import sys
from pathlib import Path

from pydantic import BaseModel, Field

# Import safe JSON utilities (Task #755, Task #983)
from formaltask.utils.json import read_json_from_file, read_json_from_stdin

# Import doc_guard_config for documented area matching (Task #903)
from formaltask.validators.doc_guard_config import matches_documented_area

# Configure module logger
logger = logging.getLogger(__name__)


class DocSuggestion(BaseModel):
    """Single documentation update suggestion."""

    file: str = Field(description="Which README.md to update")
    section: str = Field(description="Which section needs update")
    reason: str = Field(description="Why this update is needed")
    suggested_content: str = Field(description="What to add or change")


class DocAnalysisResult(BaseModel):
    """Structured output from GPT-5.1 analysis."""

    needs_update: bool = Field(description="Whether docs need updating")
    suggestions: list[DocSuggestion] = Field(default_factory=list)
    summary: str = Field(description="Brief analysis summary", min_length=20)


def analyze_commits(client, model, commits, documented_files):
    """Analyze commits using OpenRouter (Gemini 2.5 Pro) to suggest documentation updates.

    Args:
        client: OpenRouter client instance (from get_openrouter_client)
        model: Model identifier string (from get_openrouter_client)
        commits: List of commit dicts with hash, message, files keys
        documented_files: List of documented file paths

    Returns:
        DocAnalysisResult or None if no commits/files to analyze
    """
    if not commits:
        logger.debug("No commits to analyze - skipping doc analysis")
        return None
    if not documented_files:
        logger.debug("No documented files to analyze - skipping doc analysis")
        return None

    # Build commit summary with file information
    if len(commits) > 20:
        logger.warning(f"Commits truncated: {len(commits)} commits reduced to 20 for analysis")
    commit_lines = []
    for commit in commits[:20]:
        files_in_doc = [f for f in commit.get("files", []) if f in documented_files]
        if files_in_doc:
            commit_lines.append(
                f"- {commit['hash'][:7]}: {commit['message']} ({', '.join(files_in_doc)})"
            )

    if not commit_lines:
        logger.debug("No commits match documented files - skipping doc analysis")
        return None

    if len(documented_files) > 20:
        logger.warning(
            f"Documented files truncated: {len(documented_files)} files reduced to 20 for analysis"
        )

    prompt = f"""Analyze commits for documentation updates.

COMMITS:
{chr(10).join(commit_lines)}

FILES:
{chr(10).join(f"- {f}" for f in documented_files[:20])}

Should README.md be updated?"""

    try:
        result = client.chat.completions.create(
            model=model,
            response_model=DocAnalysisResult,
            messages=[{"role": "user", "content": prompt}],
        )
        return result
    except (
        # OpenAI API errors (auth, rate limit, bad request, connection)
        __import__("openai").APIError,
        __import__("openai").APIConnectionError,
        # HTTP-level errors
        __import__("httpx").RequestError,
        # Pydantic validation errors from instructor
        __import__("pydantic").ValidationError,
    ) as e:
        logger.exception("API error in analyze_commits: %s", e)
        return None


def get_openrouter_client():
    """Get OpenRouter client with instructor, or None if API key not set.

    Returns:
        Tuple of (Instructor-patched OpenRouter client, model) or (None, None) for graceful degradation
    """
    from formaltask.llm.openrouter import get_openrouter_client as _get_openrouter_client

    try:
        # Get OpenRouter client (returns tuple of (client, model))
        return _get_openrouter_client()
    except ValueError:
        # API key not configured - graceful degradation
        return (None, None)


def _validate_iso_timestamp(timestamp: str) -> bool:
    """Validate ISO 8601 timestamp format for security (Task #928)."""
    import re
    from datetime import datetime

    if not timestamp or not isinstance(timestamp, str):
        return False

    # Strict ISO 8601 pattern - rejects shell metacharacters and git args
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?$"
    if not re.match(pattern, timestamp):
        return False

    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def get_session_commits(start_time=None):
    """Get git commits from the session.

    Args:
        start_time: ISO timestamp to filter commits after (optional)

    Returns:
        List of dicts with hash, message, files keys
    """
    import subprocess

    # Security: Validate timestamp before passing to subprocess (Task #928)
    if start_time and not _validate_iso_timestamp(start_time):
        logger.warning(f"Invalid timestamp format rejected: {start_time!r}")
        return []

    # Build git log command
    cmd = ["git", "log", "--format=%H|%s", "--name-only"]
    if start_time:
        cmd.extend(["--since", start_time])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=5)
        if result.returncode != 0 or not result.stdout.strip():
            return []

        # Parse git log output (format: hash|message followed by file names)
        commits = []
        lines = result.stdout.strip().split("\n")
        current_commit = None

        for line in lines:
            if "|" in line:
                # This is a commit line (hash|message)
                if current_commit:
                    commits.append(current_commit)
                parts = line.split("|", 1)
                current_commit = {
                    "hash": parts[0],
                    "message": parts[1] if len(parts) > 1 else "",
                    "files": [],
                }
            elif line.strip() and current_commit:
                # This is a file name
                current_commit["files"].append(line.strip())

        if current_commit:
            commits.append(current_commit)

        return commits

    except (OSError, subprocess.SubprocessError, IndexError, ValueError) as e:
        import logging

        logging.getLogger(__name__).debug("get_recent_commits error: %s", e)
        return []


def load_analyzed_commits(pending_dir):
    """Load set of already-analyzed commit hashes.

    Args:
        pending_dir: Directory containing tracking file

    Returns:
        Set of commit hashes that have been analyzed
    """
    import stat
    from pathlib import Path

    tracking_file = Path(pending_dir) / "analyzed_commits.json"
    if not tracking_file.exists():
        return set()

    # Check if file is a regular file (not FIFO, device, etc.) to prevent blocking (Task #932)
    try:
        file_stat = tracking_file.stat()
        if not stat.S_ISREG(file_stat.st_mode):
            logger.warning(
                "Tracking file %s is not a regular file (mode: %o), skipping",
                tracking_file,
                file_stat.st_mode,
            )
            return set()
    except OSError as e:
        logger.warning("Cannot stat tracking file %s: %s", tracking_file, e)
        return set()

    try:
        # Use size-limited JSON reading to prevent DOS (Task #983)
        return set(read_json_from_file(str(tracking_file)))
    except (json.JSONDecodeError, TypeError, ValueError):
        return set()


def save_analyzed_commits(pending_dir, new_hashes):
    """Save analyzed commit hashes to tracking file.

    Args:
        pending_dir: Directory for tracking file
        new_hashes: List of new commit hashes to add
    """
    import json
    from pathlib import Path

    pending_dir = Path(pending_dir)
    pending_dir.mkdir(parents=True, exist_ok=True)
    tracking_file = pending_dir / "analyzed_commits.json"

    # Merge with existing
    existing = load_analyzed_commits(pending_dir)
    updated = list(existing | set(new_hashes))

    # Cap at 500 entries to prevent unbounded growth
    if len(updated) > 500:
        updated = updated[-500:]

    # Write merged hashes
    temp_file = tracking_file.with_suffix(".tmp")
    temp_file.write_text(json.dumps(updated, indent=2))
    temp_file.replace(tracking_file)


def filter_documented_files(commits):
    """Filter commit files to those in documented areas.

    Delegates to doc_guard_config.matches_documented_area() for pattern matching,
    ensuring consistency with the configured documented areas (Task #903).

    Args:
        commits: List of commit dicts with 'files' key

    Returns:
        List of file paths that are in documented areas
    """
    # Use set for O(1) lookup instead of O(n) list lookup (Task #933)
    seen = set()
    documented = []
    for commit in commits:
        for file_path in commit.get("files", []):
            if file_path not in seen and matches_documented_area(file_path):
                seen.add(file_path)
                documented.append(file_path)

    return documented


def write_pending(result, session_id, pending_dir, context=None):
    """Write analysis result to pending.json.

    Args:
        result: DocAnalysisResult or None
        session_id: Session identifier
        pending_dir: Directory for pending.json
        context: Optional dict with orientation context (files_changed, commits, branch, timestamp, topic)
    """
    if result is None:
        return

    import json
    from pathlib import Path

    pending_dir = Path(pending_dir)
    pending_dir.mkdir(parents=True, exist_ok=True)
    pending_file = pending_dir / "pending.json"

    # Load existing or start fresh using size-limited JSON (Task #983)
    if pending_file.exists():
        try:
            existing = read_json_from_file(str(pending_file))
        except (json.JSONDecodeError, ValueError):
            # Corrupted or oversized file - start fresh
            existing = []
    else:
        existing = []

    # Add new entry
    entry = result.model_dump()
    entry["session_id"] = session_id

    # Merge context for agent orientation
    if context:
        entry.update(context)

    existing.append(entry)

    # Limit to 20 entries
    if len(existing) > 20:
        existing = existing[-20:]

    # Write atomically
    temp_file = pending_file.with_suffix(".tmp")
    temp_file.write_text(json.dumps(existing, indent=2))
    temp_file.replace(pending_file)


def main():
    """Main entry point for doc analyzer worker.

    Returns:
        Exit code (0 for success, 1 for critical error)
    """
    import sys

    try:
        # Read hook data from stdin with size limits (Task #755)
        hook_data = read_json_from_stdin()

        # Explicit null check for clearer error message (Task #932)
        if hook_data is None:
            print("Error: Invalid hook data (empty or malformed input)", file=sys.stderr)
            return 1

        session_id = hook_data.get("session_id")

        if not session_id:
            print("Error: session_id required", file=sys.stderr)
            return 1

        # Get OpenRouter client (may be None, None)
        client, model = get_openrouter_client()

        # Graceful degradation: if no API key, just exit successfully
        if client is None:
            print("Warning: OPENROUTER_API_KEY not set, skipping analysis", file=sys.stderr)
            return 0

        # Setup pending directory for commit tracking
        import os
        from pathlib import Path

        project_root = os.getenv("PROJECT_ROOT", os.getcwd())
        pending_dir = Path(project_root) / ".claude" / "doc-guard"

        # Get commits and filter to documented files
        start_time = hook_data.get("start_time")
        commits = get_session_commits(start_time)

        # Filter out already-analyzed commits (deduplication)
        analyzed = load_analyzed_commits(pending_dir)
        commits = [c for c in commits if c["hash"] not in analyzed]

        if not commits:
            return 0  # All commits already analyzed

        documented_files = filter_documented_files(commits)

        if not documented_files:
            return 0

        # Analyze commits for documentation updates
        result = analyze_commits(client, model, commits, documented_files)

        if result and result.needs_update:
            write_pending(result, session_id, pending_dir)
            # Track analyzed commits to prevent duplicates
            save_analyzed_commits(pending_dir, [c["hash"] for c in commits])

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
