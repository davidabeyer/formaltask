#!/usr/bin/env python3
"""State manager for worker state (SQLite-only).

Task #1721: Create state_manager.py with locking and v1 compat.
Task #2388: Removed fsm_state/pending_question - blocking state now on tasks table.
Task #2575: Removed dead functions (update_state, locked_state_file, get_state_file_path).
Task #2703: Removed derive_worker_phase() wrapper (zero production callers).
Task #2755: Removed derive_worker_phase_with_pr(), PhaseResult, fetch_task_state -
            phase computation unified to check_completion() in core/completion_check.py.

Provides:
- get_transcript_mtime() for staleness detection from Claude session transcripts
"""

import logging
import sqlite3
from pathlib import Path

from formaltask.db.connection import DatabaseConnection
from formaltask.db.path import get_db_path
from formaltask.paths import get_claude_home


def get_transcript_mtime(
    task_id: int,
    db_path: str | Path | None = None,
    projects_dir: Path | None = None,
) -> float | None:
    """Get mtime of most recent transcript file for a task.

    Task #2378: Derive staleness from transcript mtime instead of database column.

    Args:
        task_id: Task identifier
        db_path: Path to database (for testing)
        projects_dir: Override projects directory (for testing)

    Returns:
        mtime as Unix timestamp, or None if no transcript exists.
    """
    logger = logging.getLogger(__name__)

    if db_path is None:
        try:
            db_path = get_db_path()
        except (FileNotFoundError, ValueError) as e:
            logger.debug("get_db_path() failed: %s", e)
            return None
    else:
        db_path = Path(db_path)
        if not db_path.exists():
            return None

    if projects_dir is None:
        projects_dir = get_claude_home() / "projects"

    # Get worktree_path from work_sessions
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT worktree_path FROM work_sessions WHERE current_task_id = ?",
                (task_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            worktree_path = row[0]
    except sqlite3.Error as e:
        logger.warning("Failed to get worktree_path for task-%d: %s", task_id, e)
        return None

    # Convert worktree path to Claude project naming format
    # Claude uses full path with / and . replaced by - (e.g., -Users-davidbeyer--claude-worktrees-task-123)
    project_name = worktree_path.replace("/", "-").replace(".", "-")

    # Find .jsonl files in projects directory
    project_dir = projects_dir / project_name
    if not project_dir.exists():
        return None

    jsonl_files = list(project_dir.glob("*.jsonl"))
    if not jsonl_files:
        return None

    # Return mtime of most recent file
    most_recent = max(jsonl_files, key=lambda f: f.stat().st_mtime)
    return most_recent.stat().st_mtime
