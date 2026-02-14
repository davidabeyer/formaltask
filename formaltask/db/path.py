"""Centralized database path resolution for FormalTask.

Provides get_db_path() to find the canonical formaltask.db location,
handling PROJECT_ROOT, worktrees, and security validations.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def get_db_path() -> Path:
    """Get the canonical path to formaltask.db.

    Resolution order:
    1. PROJECT_ROOT/.claude/formaltask.db (if PROJECT_ROOT env set)
    2. .task/main_repo -> main_repo/.claude/formaltask.db (worktree)
    3. cwd/.claude/formaltask.db (fallback)

    Returns:
        Path to formaltask.db

    Raises:
        FileNotFoundError: If database doesn't exist
        ValueError: If any path component is a symlink
    """
    project_root = os.environ.get("PROJECT_ROOT")
    if project_root:
        base_path = Path(project_root)
    else:
        cwd = Path.cwd()
        base_path = cwd

        # Check for worktree pointer
        task_dir = cwd / ".task"
        if task_dir.exists():
            for filename in ["project_root", "main_repo"]:
                repo_file = task_dir / filename
                if repo_file.exists():
                    try:
                        content = repo_file.read_text().strip()
                        if content:
                            main_repo = Path(content)
                            if not main_repo.is_symlink():
                                base_path = main_repo.resolve()
                                break
                    except (OSError, UnicodeDecodeError) as e:
                        logger.debug("Failed to read %s: %s", repo_file, e)

    claude_dir = base_path / ".claude"
    db_path = claude_dir / "formaltask.db"

    # Security: reject symlinks
    if claude_dir.is_symlink():
        raise ValueError(f"Symlink not allowed for .claude directory: {claude_dir}")
    if db_path.is_symlink():
        raise ValueError(f"Symlink not allowed for database file: {db_path}")

    if not db_path.exists():
        raise FileNotFoundError(f"formaltask.db not found at {db_path}")

    # Security: reject home directory database (wrong location for project work)
    home_claude_db = Path.home() / ".claude" / "formaltask.db"
    if db_path.resolve() == home_claude_db.resolve():
        raise ValueError(
            f"Refusing to use home directory database: {db_path}\n"
            f"Set PROJECT_ROOT or run from project directory.\n"
            f"Hint: export PROJECT_ROOT=/path/to/your/project"
        )

    return db_path


# System directories that should never be accessed (Task #1965)
BLOCKED_SYSTEM_DIRS = frozenset(["/dev", "/proc", "/sys", "/etc", "/var", "/boot", "/root"])


def validate_user_db_path(path_str: str) -> Path:
    """Validate user-provided database path from --db-path argument.

    Security checks applied (Task #1965, Task #1911):
    - Block system directories (/dev, /proc, /sys, /etc) - checked first to avoid PermissionError
    - Reject symlinks (prevent symlink attacks)
    - Require .db extension (ensure database file)
    - Verify file exists

    Args:
        path_str: User-provided path string from --db-path argument

    Returns:
        Validated Path object

    Raises:
        ValueError: If path fails any validation check
    """
    path = Path(path_str)

    # Block system directories FIRST (before is_symlink/resolve which can raise PermissionError)
    # Only use string operations to avoid filesystem access on protected paths
    path_str_abs = str(path.absolute())
    for blocked in BLOCKED_SYSTEM_DIRS:
        if path_str_abs.startswith(blocked + "/") or path_str_abs == blocked:
            raise ValueError(f"Path in blocked system directory: {path}")

    # Require .db extension (string check, no filesystem access)
    if path.suffix.lower() != ".db":
        raise ValueError(f"Path must have .db extension: {path}")

    # Reject symlinks to prevent symlink attacks (filesystem access)
    if path.is_symlink():
        raise ValueError(f"Path is a symlink: {path}")

    # Check resolved path for system directories (after symlink check, handles /etc -> /private/etc)
    resolved_str = str(path.resolve())
    for blocked in BLOCKED_SYSTEM_DIRS:
        if resolved_str.startswith(blocked + "/") or resolved_str == blocked:
            raise ValueError(f"Path in blocked system directory: {path}")

    # Verify file exists
    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")

    return path
