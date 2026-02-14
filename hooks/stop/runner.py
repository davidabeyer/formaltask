#!/usr/bin/env python3
"""Stop hook entry point - plain function architecture.

Task #2570: Simplified to use check_completion directly.
"""

import json
import logging
import sys
from pathlib import Path

# Add project root for imports when run directly
_project_root = str(Path(__file__).parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _get_task_id_from_cwd(cwd: str | None) -> int | None:
    """Extract task ID from worktree .task/id file."""
    if not cwd:
        return None
    task_id_file = Path(cwd) / ".task" / "id"
    if not task_id_file.exists():
        return None
    try:
        return int(task_id_file.read_text().strip())
    except (ValueError, OSError):
        return None


def _get_db_path_from_cwd(cwd: str | None) -> str | None:
    """Get database path from worktree .task/main_repo or project_root file."""
    if not cwd:
        return None
    cwd_path = Path(cwd)

    # Priority: main_repo > project_root > cwd
    main_repo_file = cwd_path / ".task" / "main_repo"
    project_root_file = cwd_path / ".task" / "project_root"

    if main_repo_file.exists():
        try:
            main_repo = Path(main_repo_file.read_text().strip())
            db_path = main_repo / ".claude" / "formaltask.db"
            if db_path.exists():
                return str(db_path)
        except OSError:
            pass

    if project_root_file.exists():
        try:
            project_root = Path(project_root_file.read_text().strip())
            db_path = project_root / ".claude" / "formaltask.db"
            if db_path.exists():
                return str(db_path)
        except OSError:
            pass

    # Fallback to cwd
    db_path = cwd_path / ".claude" / "formaltask.db"
    if db_path.exists():
        return str(db_path)

    return None


def main() -> dict:
    """Execute stop hook."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return {}  # Fail-open on malformed input

    # Loop prevention
    if input_data.get("stop_hook_active"):
        return {}

    cwd = input_data.get("cwd")
    task_id = _get_task_id_from_cwd(cwd)

    # Not a worker? Exit immediately.
    if task_id is None:
        return {}

    db_path = _get_db_path_from_cwd(cwd)

    # Build context and run all phases
    from hooks.stop.phases.completion_enforcer import PHASES

    ctx = {
        "task_id": task_id,
        "db_path": db_path,
        "transcript_path": input_data.get("transcript_path"),
        "stop_hook_active": input_data.get("stop_hook_active", False),
    }

    for phase_fn in PHASES:
        try:
            result = phase_fn(ctx)
        except Exception as e:
            logging.getLogger(__name__).debug("Phase %s error: %s", phase_fn.__name__, e)
            continue
        if result:  # First blocking phase wins
            return result

    return {}


if __name__ == "__main__":
    print(json.dumps(main()))
