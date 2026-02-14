#!/usr/bin/env python3
"""PreToolUse Hook: Block write SQL access to FormalTask database.

Allows read-only queries (SELECT) but blocks writes (INSERT, UPDATE, DELETE, etc.)
to prevent data corruption while enabling search and inspection.
"""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import json
import re
import sys

# SQL keywords that indicate write operations
WRITE_KEYWORDS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bCREATE\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bREPLACE\b",
    r"\bMERGE\b",
]

BLOCKED_MESSAGE = (
    "BLOCKED: Write SQL to formaltask.db not allowed. Use CLI: python3 -m formaltask.cli.pm <cmd>"
)

# Patterns that indicate Python-based DB bypass attempts
PYTHON_DB_BYPASS_PATTERNS = [
    r"DatabaseConnection",
    r"formaltask\.db",
    r"formaltask/db/",
    r"transition_task_status",
    r"\.execute\s*\([^)]*(?:UPDATE|INSERT|DELETE)",
]

WORKTREE_BLOCKED_MESSAGE = (
    "BLOCKED: Direct DB write not allowed in task worktree.\n\n"
    "Workers cannot bypass review gates or modify task state directly.\n"
    "If you need human intervention, run:\n\n"
    '  ft work blocked "<describe what you need and why CLI can\'t do it>"\n\n'
    "Human can then fix from master or approve the operation."
)


def _is_task_worktree() -> bool:
    """Check if running in a task worktree (not master).

    Detects worktree via .task/ directory which is created for all task worktrees.
    """
    from pathlib import Path

    return Path(".task").exists()


def _is_python_db_bypass(command: str) -> bool:
    """Detect Python DB bypass: python command + bypass pattern + write keyword."""
    if not command or "python" not in command.lower():
        return False
    return any(
        re.search(p, command, re.IGNORECASE) and is_write_query(command)
        for p in PYTHON_DB_BYPASS_PATTERNS
    )


def check(ctx: dict) -> dict | None:
    """Validate command doesn't write to formaltask.db.

    Args:
        ctx: Hook context dict with tool_name and tool_input.

    Returns:
        None if allowed (non-Bash, non-formaltask, or read-only query),
        dict with decision='block' and reason if write query detected.
    """
    tool_name = ctx.get("tool_name", "")

    # Only validate Bash tool
    if tool_name != "Bash":
        return None

    command = ctx.get("tool_input", {}).get("command", "")
    if not command:
        return None

    # Block Python DB bypass in task worktrees
    if _is_task_worktree() and _is_python_db_bypass(command):
        return {"decision": "block", "reason": WORKTREE_BLOCKED_MESSAGE}

    if not is_direct_sql_to_formaltask(command):
        return None

    # Check for wrong database path before processing
    db_path = extract_db_path_from_command(command)
    if db_path and is_wrong_db_path(db_path):
        correct_path = get_correct_db_path()
        if correct_path:
            return {
                "decision": "block",
                "reason": f"BLOCKED: Wrong DB path {db_path}. Use: {correct_path}",
            }

    if not is_write_query(command):
        return None

    return {"decision": "block", "reason": BLOCKED_MESSAGE}


def is_direct_sql_to_formaltask(command: str) -> bool:
    """Detect if command is direct sqlite3 access to formaltask.db."""
    if not command or "sqlite3" not in command.lower():
        return False

    patterns = [
        r'sqlite3\s+["\']?[^"\']*formaltask\.db',  # Direct filename
        r'sqlite3\s+"\$DB_PATH"',  # Variable reference (common pattern)
        r"sqlite3\s+\$DB_PATH\b",  # Unquoted variable
    ]

    return any(re.search(pattern, command, re.IGNORECASE) for pattern in patterns)


def extract_db_path_from_command(command: str) -> str | None:
    """Extract database path from sqlite3 command."""
    match = re.search(r"sqlite3\s+(?!-)(\S+)", command or "", re.IGNORECASE)
    return match.group(1).strip("\"'") if match else None


def is_write_query(command: str) -> bool:
    """Detect if SQL command contains write operations."""
    return any(re.search(keyword, command, re.IGNORECASE) for keyword in WRITE_KEYWORDS)


def is_wrong_db_path(db_path: str) -> bool:
    """Detect if db_path points to ~/.claude/formaltask.db (wrong location).

    The correct location is $PROJECT_ROOT/.claude/formaltask.db.
    This detects agents accessing the wrong database in home directory.

    Args:
        db_path: Database path to check

    Returns:
        True if path is ~/.claude/formaltask.db pattern, False otherwise
    """
    if not db_path or "formaltask.db" not in db_path:
        return False

    # Normalize ~ to absolute path for comparison
    import os

    expanded = os.path.expanduser(db_path)

    # Check if it's in ~/.claude/ directly (not a project subdirectory)
    home_claude = os.path.expanduser("~/.claude/formaltask.db")
    if expanded == home_claude:
        return True

    # Also match unexpanded tilde path
    if db_path == "~/.claude/formaltask.db":
        return True

    # Match /Users/*/.claude/formaltask.db or /home/*/.claude/formaltask.db
    # but NOT /Users/*/projects/something/.claude/formaltask.db
    pattern = r"^(/Users/[^/]+|/home/[^/]+)/\.claude/formaltask\.db$"
    return bool(re.match(pattern, expanded))


def get_correct_db_path() -> str | None:
    """Get the correct database path from environment or worktree context.

    Resolution order:
    1. PROJECT_ROOT environment variable
    2. .task/project_root file (worktree context)
    3. .task/main_repo file (worktree context, legacy)

    Returns:
        Correct database path, or None if no context available
    """
    import os
    from pathlib import Path

    # 1. Check PROJECT_ROOT environment variable
    project_root = os.environ.get("PROJECT_ROOT")
    if project_root:
        return f"{project_root}/.claude/formaltask.db"

    # 2. Check for worktree context files
    task_dir = Path(".task")
    if task_dir.exists():
        # Try project_root first
        project_root_file = task_dir / "project_root"
        if project_root_file.exists():
            root = project_root_file.read_text().strip()
            return f"{root}/.claude/formaltask.db"

        # Legacy: try main_repo
        main_repo_file = task_dir / "main_repo"
        if main_repo_file.exists():
            root = main_repo_file.read_text().strip()
            return f"{root}/.claude/formaltask.db"

    return None


def main() -> None:
    """Hook entry point."""
    try:
        ctx = json.load(sys.stdin)
        result = check(ctx)
        if result:
            print(json.dumps(result))
    except json.JSONDecodeError:
        # Fail open for malformed input
        pass


if __name__ == "__main__":
    main()
