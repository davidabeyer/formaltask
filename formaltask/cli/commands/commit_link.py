"""pm-commit-link command - Manually link a commit to a task."""

import argparse
import subprocess
from pathlib import Path

from formaltask.cli.base import CLIError
from formaltask.cli.context import with_db_path
from formaltask.cli.output import OutputFormatter
from formaltask.db.connection import DatabaseConnection
from formaltask.tasks import get_task

# Plugin interface exports
COMMAND_NAME = "commit-link"
COMMAND_HELP = "Manually link a commit to a task"


def setup_parser(subparser):
    """Set up argument parser for commit-link command."""
    subparser.add_argument("task_id", type=int, help="Task ID to link to")
    subparser.add_argument("commit_hash", help="Git commit hash")
    subparser.add_argument(
        "--message", help="Custom commit message (uses git message if not provided)"
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
    """Execute the commit-link command."""
    formatter = OutputFormatter(args) if getattr(args, "json", False) else None

    try:
        result = commit_link(
            task_id=args.task_id,
            commit_hash=args.commit_hash,
            db_path=db_path,
            repo_path=args.repo_path,
            message=args.message,
        )

        if formatter:
            print(formatter.success(result, "Linked commit to task #{task_id}"))
        elif result["linked"]:
            print(f"✓ Linked commit {args.commit_hash[:8]} to task #{args.task_id}")
        else:
            print(f"⊘ Commit already linked to task #{args.task_id}")
        return 0
    except CLIError as e:
        if formatter:
            print(formatter.error(e))
        else:
            print(f"Error: {e.message}")
        return e.exit_code.value if hasattr(e.exit_code, "value") else int(e.exit_code)


def commit_link(task_id, commit_hash, db_path: str, repo_path=None, message=None):
    """Link a commit to a task.

    Args:
        task_id: Task ID to link to
        commit_hash: Git commit hash
        db_path: Path to the database
        repo_path: Optional path to git repository
        message: Optional custom commit message

    Returns:
        dict with result details

    Raises:
        CLIError: If task not found, commit not found, or invalid input
    """
    # Validate commit_hash is not empty
    if not commit_hash or not commit_hash.strip():
        raise CLIError("commit_hash cannot be empty")

    # Validate repo_path exists if provided
    if repo_path is not None and not Path(repo_path).exists():
        raise CLIError(f"Repository path does not exist: {repo_path}")

    # Validate task exists
    task = get_task(db_path, task_id)
    if task is None:
        raise CLIError(f"Task #{task_id} not found")

    # Validate commit exists in git (^{commit} ensures object exists and is a commit)
    try:
        subprocess.run(
            ["git", "rev-parse", "--verify", f"{commit_hash}^{{commit}}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except subprocess.CalledProcessError:
        raise CLIError(f"Commit {commit_hash} not found in git history") from None

    # Get commit message from git if not provided
    if message is None:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%B", commit_hash],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        message = result.stdout.strip()

    # Insert into database
    with DatabaseConnection(db_path) as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO commits (task_id, commit_hash, commit_message) VALUES (?, ?, ?)",
            (task_id, commit_hash, message),
        )
        linked = cursor.rowcount > 0

    result = {
        "linked": linked,
        "task_id": task_id,
        "commit_hash": commit_hash,
        "commit_message": message,
    }
    if not linked:
        result["skipped"] = True
    return result
