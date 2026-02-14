"""pm-commit-scan command - Scan git commits and link to tasks."""

import argparse
import re
import subprocess
from pathlib import Path

from formaltask.cli.base import CLIError
from formaltask.cli.context import with_db_path
from formaltask.cli.output import OutputFormatter
from formaltask.db.connection import DatabaseConnection

# ASCII Record Separator - can't appear in commit messages (non-printable)
COMMIT_DELIMITER = "\x1e"


def _extract_task_refs(message: str, task_id: int | None = None) -> set[int]:
    """Extract task references from commit message."""
    pattern = r"(?:refs |fixes |closes |Task: )?#(\d+)"
    refs = {int(m.group(1)) for m in re.finditer(pattern, message)}
    if task_id is not None:
        refs = {tid for tid in refs if tid == task_id}
    return refs


def _batch_insert_commit_links(db_path: str, links: list[tuple[int, str, str]]) -> tuple[int, int]:
    """Batch insert commit links and return counts.

    Args:
        db_path: Path to database
        links: List of (task_id, commit_hash, message) tuples

    Returns:
        Tuple of (linked_count, skipped_count)
    """
    if not links:
        return 0, 0

    linked_count = 0
    skipped_count = 0
    with DatabaseConnection(db_path) as conn:
        for tid, commit_hash, message in links:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO commits (task_id, commit_hash, commit_message) VALUES (?, ?, ?)",
                (tid, commit_hash, message),
            )
            if cursor.rowcount > 0:
                linked_count += 1
            else:
                skipped_count += 1
    return linked_count, skipped_count


def _parse_commits(git_output: str) -> list[tuple[str, str, str]]:
    """Parse git log output into list of (hash, subject, body) tuples."""
    if not git_output.strip():
        return []

    commits = []
    current_commit = []

    for line in git_output.strip().split("\n"):
        if COMMIT_DELIMITER in line:
            if current_commit:
                commits.append("\n".join(current_commit))
            current_commit = [line]
        elif current_commit:
            current_commit.append(line)

    if current_commit:
        commits.append("\n".join(current_commit))

    result = []
    for commit_text in commits:
        parts = commit_text.split(COMMIT_DELIMITER, 2)
        if len(parts) >= 3:
            result.append((parts[0], parts[1], parts[2]))
    return result


# Plugin interface exports
COMMAND_NAME = "commit-scan"
COMMAND_HELP = "Scan git commits and link to tasks"


def setup_parser(subparser):
    """Set up argument parser for commit-scan command."""
    subparser.add_argument("--task-id", type=int, help="Only scan for specific task ID")
    subparser.add_argument(
        "--since",
        help="Only scan commits since date (ISO 8601: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)",
    )
    subparser.add_argument(
        "--repo-path", help="Path to git repository (defaults to current directory)"
    )
    subparser.add_argument(
        "--db-path",
        default=None,
        help="Database path (default: auto-detect)",
    )


@with_db_path
def execute(db_path: str, args: argparse.Namespace) -> int:
    """Execute the commit-scan command."""
    formatter = OutputFormatter(args) if getattr(args, "json", False) else None

    try:
        result = commit_scan(
            db_path=db_path,
            task_id=getattr(args, "task_id", None),
            since=getattr(args, "since", None),
            repo_path=getattr(args, "repo_path", None),
        )
        if formatter:
            print(formatter.success(result, "Linked {linked_count} commits"))
        else:
            print(f"✓ Scanned commits, linked {result['linked_count']} to tasks")
        return 0
    except CLIError as e:
        if formatter:
            print(formatter.error(e))
        else:
            print(f"Error: {e.message}")
        return e.exit_code.value if hasattr(e.exit_code, "value") else int(e.exit_code)


def commit_scan(db_path: str, task_id=None, since=None, repo_path=None):
    """Scan git log for task references and link commits.

    Supported patterns: refs #123, fixes #123, closes #123, Task: #123, #123

    Args:
        db_path: Path to the database
        task_id: Optional task ID to filter commits (must be positive int or None)
        since: Optional date filter (ISO 8601 format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)
        repo_path: Optional path to git repository (must exist if provided)

    Raises:
        CLIError: If task_id is not a positive integer, repo_path doesn't exist,
                  or date format is invalid
    """
    # Input validation
    if task_id is not None and (not isinstance(task_id, int) or task_id <= 0):
        raise CLIError(f"task_id must be a positive integer, got: {task_id}")

    if repo_path is not None and not Path(repo_path).exists():
        raise CLIError(f"repo_path does not exist: {repo_path}")

    # Build git log command
    cmd = ["git", "log", f"--format=%H{COMMIT_DELIMITER}%s{COMMIT_DELIMITER}%B", "--all"]
    if since:
        # Input validation - shlex.quote() is NOT needed for list-style subprocess
        # Pattern allows: digits, hyphens, colons, T, Z (ISO 8601 date format)
        if not re.match(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$", since):
            raise CLIError(f"Invalid date format: {since}")
        cmd.append(f"--since={since}")

    # Run git log - gracefully handle non-git directories
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, cwd=repo_path, timeout=30
        )
    except subprocess.CalledProcessError:
        # Not a git repo or git command failed - return empty result
        return {"linked_count": 0, "skipped_count": 0}

    # Task #2005: Use extracted helpers to reduce complexity
    links_to_insert = []
    for commit_hash, subject, body in _parse_commits(result.stdout):
        full_message = f"{subject}\n{body}"
        task_refs = _extract_task_refs(full_message, task_id)
        for tid in task_refs:
            links_to_insert.append((tid, commit_hash, full_message))

    # Batch insert using helper
    linked_count, skipped_count = _batch_insert_commit_links(db_path, links_to_insert)
    return {"linked_count": linked_count, "skipped_count": skipped_count}
