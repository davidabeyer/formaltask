"""Path resolution for formaltask."""

from __future__ import annotations

import os
from pathlib import Path

__all__ = [
    "get_claude_home",
    "get_project_root",
    "get_projects_dir",
    "get_hook_script_path",
    "get_workflow_worker_logs_dir",
    "task_worktree",
]

MAX_PARENT_SEARCH_DEPTH = 3


def get_claude_home() -> Path:
    """CLAUDE_HOME env var or ~/.claude."""
    claude_home = os.environ.get("CLAUDE_HOME")
    if claude_home:
        path = Path(claude_home)
        if not path.is_absolute():
            raise ValueError(f"CLAUDE_HOME must be an absolute path, got: {claude_home}")
        return path
    return Path.home() / ".claude"


def get_project_root() -> Path:
    """PROJECT_ROOT env var, or search upward for .claude/ or CLAUDE.md."""
    project_root = os.environ.get("PROJECT_ROOT")
    if project_root:
        path = Path(project_root)
        if not path.is_absolute():
            raise ValueError(f"PROJECT_ROOT must be an absolute path, got: {project_root}")
        return path

    markers = [".claude", "CLAUDE.md"]
    cwd = Path.cwd()
    candidates = [cwd] + list(cwd.parents)[:MAX_PARENT_SEARCH_DEPTH]

    for candidate in candidates:
        for marker in markers:
            if (candidate / marker).exists():
                return candidate

    raise ValueError(
        "Could not detect project root. Either:\n"
        "  - Run from a directory containing .claude/ or CLAUDE.md\n"
        "  - Set PROJECT_ROOT environment variable"
    )


def get_hook_script_path(relative_path: str) -> str:
    """Absolute path to a hook script under project root."""
    if ".." in Path(relative_path).parts:
        raise ValueError(f"path traversal rejected: {relative_path}")
    return str(get_project_root() / relative_path)


def get_workflow_worker_logs_dir() -> Path:
    """CLAUDE_HOME/workflow-worker/logs."""
    return get_claude_home() / "workflow-worker" / "logs"


def get_projects_dir() -> Path:
    """FORMALTASK_PROJECTS_DIR env var or ~/projects."""
    d = os.environ.get("FORMALTASK_PROJECTS_DIR")
    if d:
        path = Path(d)
        if not path.is_absolute():
            raise ValueError(f"FORMALTASK_PROJECTS_DIR must be absolute, got: {d}")
        return path
    return Path.home() / "projects"


def task_worktree(task_id: int) -> Path:
    """CLAUDE_HOME/worktrees/task-{id}."""
    return get_claude_home() / "worktrees" / f"task-{task_id}"
