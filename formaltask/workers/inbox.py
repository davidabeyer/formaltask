"""Inbox module for blocked workers management.

Task #2148: Rewrite Inbox Command with Interactive UI.
Task #2378: Switch ordering to transcript mtime instead of last_heartbeat.
Task #2388: Now queries tasks.status='blocked_user' (workers.fsm_state removed).

Provides:
- get_blocked_workers(db_path) - Query tasks WHERE status='blocked_user'

Note: Worker resume is handled by formaltask.workers.resume.resume_worker_in_tmux()
which is called by the `pm resume` CLI command.
"""

import sqlite3
import time
from pathlib import Path

from formaltask.db.connection import DatabaseConnection
from formaltask.state.manager import get_transcript_mtime

__all__ = [
    "get_blocked_workers",
]


def get_blocked_workers(
    db_path: str,
    projects_dir=None,
) -> list[dict]:
    """Query blocked workers with task information.

    Task #2388: Now queries tasks table (workers.fsm_state/pending_question removed).

    Args:
        db_path: Path to the database file.
        projects_dir: Override projects directory (for testing)

    Returns:
        List of dicts with blocked worker information (ordered by transcript mtime ASC):
        - task_id: The task ID
        - task_title: Title of the task
        - pending_question: The question the worker is blocked on (from tasks.blocked_question)
        - age_seconds: How long the worker has been blocked (from transcript mtime)
    """
    with DatabaseConnection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                t.id as task_id,
                t.title as task_title,
                t.blocked_question as pending_question
            FROM tasks t
            WHERE t.status = 'blocked_user'
        """)
        workers = [dict(row) for row in cursor.fetchall()]

    # Task #2378: Enrich with age and sort by transcript mtime (oldest first)
    now = time.time()
    enriched = []
    for worker in workers:
        mtime = get_transcript_mtime(
            worker["task_id"],
            db_path=db_path,
            projects_dir=Path(projects_dir) if projects_dir else None,
        )
        worker["age_seconds"] = int(now - mtime) if mtime else None
        enriched.append((mtime or 0, worker))

    return [w for _, w in sorted(enriched)]
