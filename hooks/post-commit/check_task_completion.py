#!/usr/bin/env python3
"""
Post-Commit Hook - Check Task Completion

Warns if commit was made while tasks are still in-progress.
"""

import os
from pathlib import Path

from formaltask.db.connection import DatabaseConnection


def check_incomplete_tasks() -> None:
    """Check for incomplete tasks and print warning if found."""
    # Get database path from environment variable
    if "FORMALTASK_DB_PATH" not in os.environ:
        return

    db_path = Path(os.environ["FORMALTASK_DB_PATH"])

    if not db_path.exists():
        return

    # Query for in-progress tasks
    with DatabaseConnection(str(db_path)) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title
            FROM tasks
            WHERE started_at IS NOT NULL
              AND completed_at IS NULL
            ORDER BY id
        """)

        tasks = cursor.fetchall()

    if tasks:
        print()
        print("⚠️  Warning: Tasks still in-progress after commit")
        print("   Remember to complete tasks when done:")
        print()
        for task_id, title in tasks:
            print(f"   • Task #{task_id}: {title}")
            print(f"     Complete with: /pm-task-complete {task_id}")
        print()
