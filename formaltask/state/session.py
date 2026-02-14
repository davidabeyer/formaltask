"""Worktree session tracking - standalone functions.

Extracted from EpicRepository (Task #1937), refactored to antirez-style
functions (Task #2627). Manages work_sessions table.
"""

from formaltask.db.connection import DatabaseConnection

__all__: list[str] = ["get_current_task", "set_current_task"]


def get_current_task(db_path: str, worktree_path: str) -> int | None:
    """Get current task for worktree.

    Args:
        db_path: Path to SQLite database file
        worktree_path: Path to the git worktree

    Returns:
        Task ID or None if no session exists for this worktree
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT current_task_id FROM work_sessions WHERE worktree_path = ?",
            (worktree_path,),
        )
        result = cursor.fetchone()
        return result[0] if result else None


def set_current_task(db_path: str, worktree_path: str, task_id: int) -> None:
    """Set current task for worktree (upsert)."""
    with DatabaseConnection(db_path) as conn:
        conn.execute(
            """INSERT INTO work_sessions (worktree_path, current_task_id)
               VALUES (?, ?)
               ON CONFLICT(worktree_path) DO UPDATE SET current_task_id = ?""",
            (worktree_path, task_id, task_id),
        )
