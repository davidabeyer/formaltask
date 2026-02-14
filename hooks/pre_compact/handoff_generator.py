"""PreCompact hook: generate handoff documents before compaction.

Captures conversation context when compaction fires, generating structured
handoff documents via GPT 5.2. Activation is via worktree session ONLY.

Usage:
    1. Start session via `cc thread-name` (creates .session/name file)
    2. Work continues...
    3. User runs /compact → handoff generated automatically

Detection:
    - Checks for .session/name file in cwd
    - If found, uses thread name from file and full transcript
    - If not found, returns None (no handoff generated)
"""

import json
import logging
import os
import sys
from pathlib import Path

# Add project root for imports when run directly
_project_root = str(Path(__file__).parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from pydantic import BaseModel, Field

from formaltask.llm.openrouter import get_openrouter_client
from hooks.pre_compact.handoff_transcript import handoff_transcript
from hooks.pre_compact.handoff_writer import (
    HANDOFF_DIR,
    PROJECTS_DIR,
    write_handoff,
    write_stub_handoff,
    write_thread_breadcrumb,
)

logger = logging.getLogger(__name__)

HANDOFF_MODEL = "openai/gpt-5.2"

SYSTEM_PROMPT = """You are extracting a handoff document from a conversation transcript.

Create a structured handoff that lets a future session pick up exactly where this one left off.

Focus on:
- Decision RATIONALE, not just what was decided
- Failed approaches and why they failed
- Blockers, constraints, gotchas discovered
- Context that would be lost without capture

Keep summaries concise but complete."""


class HandoffResponse(BaseModel):
    """Structured handoff response from LLM."""

    summary: str = Field(max_length=500, description="Brief summary of what was accomplished")
    decisions: list[str] = Field(default_factory=list, description="Key decisions with rationale")
    completed: list[str] = Field(default_factory=list, description="Tasks/items completed")
    pending: list[str] = Field(default_factory=list, description="Tasks/items still pending")
    context: str = Field(default="", description="Additional context for continuity")
    files_touched: list[str] = Field(default_factory=list, description="Files modified or read")


def generate_handoff(
    ctx: dict, *, handoff_dir: Path = HANDOFF_DIR, projects_dir: Path = PROJECTS_DIR
) -> Path | None:
    """Generate handoff document from transcript.

    Activation: .session/name file in cwd (worktree-only).

    Args:
        ctx: PreCompact hook context with transcript_path, cwd, and optional project_id.
        handoff_dir: Directory for handoff output.
        projects_dir: Directory for project files (breadcrumb storage).

    Returns:
        Path to written handoff file, or None if no .session/name found.
    """
    transcript_path_str = ctx.get("transcript_path")
    if not transcript_path_str:
        logger.debug("No transcript_path in context")
        return None

    transcript_path = Path(transcript_path_str)
    if not transcript_path.exists():
        logger.debug("Transcript path does not exist: %s", transcript_path)
        return None

    # Check for worktree session file - ONLY activation method
    cwd = Path(ctx.get("cwd", os.getcwd()))
    session_name_file = cwd / ".session" / "name"

    if not session_name_file.exists():
        logger.debug("No .session/name found - skipping handoff")
        return None

    thread_name = session_name_file.read_text().strip()
    start_line = 0  # Full transcript for worktree sessions
    logger.debug("Worktree session detected: %s", thread_name)

    # Extract conversation (from marker or full transcript)
    conversation = handoff_transcript(transcript_path, start_line=start_line)

    # Call LLM
    try:
        client, model = get_openrouter_client(model=HANDOFF_MODEL)

        response = client.chat.completions.create(
            model=model,
            response_model=HandoffResponse,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Extract a handoff from this conversation:\n\n{conversation}",
                },
            ],
        )

        content = {
            "summary": response.summary,
            "decisions": response.decisions,
            "completed": response.completed,
            "pending": response.pending,
            "context": response.context,
            "files_touched": response.files_touched,
        }

        result = write_handoff(thread_name, content, handoff_dir=handoff_dir)

        # Write breadcrumb for session-start to find
        project_id = ctx.get("project_id")
        if project_id:
            write_thread_breadcrumb(thread_name, project_id, projects_dir=projects_dir)

        return result

    except Exception as e:
        logger.warning("Handoff generation failed: %s", e)
        result = write_stub_handoff(
            thread_name,
            transcript_path=str(transcript_path),
            error=str(e),
            handoff_dir=handoff_dir,
        )

        # Write breadcrumb even on failure so session can resume
        project_id = ctx.get("project_id")
        if project_id:
            write_thread_breadcrumb(thread_name, project_id, projects_dir=projects_dir)

        return result


def main() -> None:
    """Entry point for PreCompact hook."""
    payload = json.load(sys.stdin)
    generate_handoff(payload)


if __name__ == "__main__":
    main()
