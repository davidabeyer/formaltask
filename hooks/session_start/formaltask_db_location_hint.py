#!/usr/bin/env python3
"""SessionStart hook to warn agents about FormalTask database location in worktrees."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_main_repo_db_path(cwd: Path) -> str | None:
    """Get the main repo's formaltask.db path if in a worktree."""
    task_dir = cwd / ".task"
    if not task_dir.exists():
        return None

    # Check main_repo or project_root file (both contain main repo path)
    for filename in ["main_repo", "project_root"]:
        repo_file = task_dir / filename
        if repo_file.exists():
            try:
                main_repo = Path(repo_file.read_text().strip())
                db_path = main_repo / ".claude" / "formaltask.db"
                if db_path.exists():
                    return str(db_path)
            except OSError as e:
                logger.debug("OSError reading %s, trying next: %s", filename, e)

    return None


def get_home_claude_db_path() -> Path:
    """Get ~/.claude/formaltask.db path (common misconception location)."""
    return Path.home() / ".claude" / "formaltask.db"


def process(data: dict) -> dict:
    """Process hook data and return result.

    This function can be called directly by the dispatcher.

    Args:
        data: Hook input with optional 'cwd' field.

    Returns:
        Hook output dict with warning context, or empty dict.
    """
    cwd = Path(data.get("cwd", ".")) if data.get("cwd") else Path.cwd()
    db_path = get_main_repo_db_path(cwd)
    local_db = cwd / ".claude" / "formaltask.db"
    home_claude_db = get_home_claude_db_path()

    # Warn if in worktree and either local db or ~/.claude/formaltask.db could confuse
    if db_path:
        confusing_db_exists = local_db.exists() or home_claude_db.exists()
        if confusing_db_exists:
            warning = (
                f"<formaltask_database_warning>"
                f"FormalTask DB is at {db_path} - NOT ~/.claude/formaltask.db. "
                f"Use --db-path {db_path} or sqlite3 {db_path}"
                f"</formaltask_database_warning>"
            )
            return {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": warning,
                }
            }

    return {}


def main() -> None:
    """Entry point for SessionStart hook (stdout-based)."""
    result = process({})
    if result:
        print(json.dumps(result))
    else:
        print("{}")


if __name__ == "__main__":
    main()
