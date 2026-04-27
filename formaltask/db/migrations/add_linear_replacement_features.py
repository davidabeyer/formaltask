"""Migration: add task_comments table, due_date and priority columns.

Part of linear-to-ft project — adds features needed to replace Linear.
Idempotent: safe to run multiple times.
"""

from formaltask.db.connection import DatabaseConnection
from formaltask.db.migrations.helpers import (
    column_exists,
    record_migration,
    table_exists,
)

MIGRATION_NAME = "add_linear_replacement_features"


def migrate(db_path: str) -> bool:
    """Add task_comments table and due_date/priority columns to tasks.

    Returns True if any changes were made.
    """
    changed = False

    with DatabaseConnection(str(db_path)) as conn:
        cursor = conn.cursor()

        # Create task_comments table
        if not table_exists(cursor, "task_comments"):
            cursor.execute("""
                CREATE TABLE task_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_task_comments_task_id ON task_comments(task_id)"
            )
            changed = True

        # Add due_date column
        if not column_exists(cursor, "tasks", "due_date"):
            cursor.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")
            changed = True

        # Add priority column
        if not column_exists(cursor, "tasks", "priority"):
            cursor.execute("ALTER TABLE tasks ADD COLUMN priority INTEGER")
            changed = True

        if changed:
            record_migration(cursor, MIGRATION_NAME)

    return changed
