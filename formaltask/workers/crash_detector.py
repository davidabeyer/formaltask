"""Find orphaned workers (in_progress tasks with dead tmux sessions)."""

import sqlite3
from pathlib import Path

from formaltask.db.connection import DatabaseConnection
from formaltask.db.path import get_db_path
from formaltask.tmux import is_pane_alive
from formaltask.tmux import session_exists as tmux_session_exists


def get_orphaned_workers(db_path: Path | str | None = None) -> list[int]:
    """Find in_progress tasks with dead or missing workers."""
    if db_path is None:
        try:
            db_path = get_db_path()
        except (FileNotFoundError, ValueError):
            return []
    else:
        db_path = Path(db_path)
        if not db_path.exists():
            return []

    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute("SELECT id FROM tasks WHERE status = 'in_progress'")
            orphaned = []
            for row in cursor.fetchall():
                task_id = row["id"]
                session_name = f"task-{task_id}"
                if not tmux_session_exists(session_name) or not is_pane_alive(session_name):
                    orphaned.append(task_id)
            return orphaned
    except sqlite3.Error:
        return []
