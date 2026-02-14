"""Drop task_events table (Task #2770).

Removes dead infrastructure: table, 5 indexes, 1 trigger.
task_events was event sourcing for task lifecycle but the data was never read.
Python write code removed in Task #2769.
"""

from formaltask.db.connection import DatabaseConnection
from formaltask.db.migrations.helpers import migration_applied, record_migration, table_exists


def migrate(db_path: str) -> bool:
    """Drop task_events table, indexes, and trigger.

    Idempotent - safe to run multiple times.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        True if anything was dropped, False otherwise.
    """
    with DatabaseConnection(str(db_path)) as conn:
        cursor = conn.cursor()

        # Skip if already applied
        if migration_applied(cursor, "drop_task_events"):
            return False

        dropped = False

        # Drop trigger first (depends on table)
        cursor.execute("DROP TRIGGER IF EXISTS task_events_no_delete")

        # Drop indexes (depend on table)
        cursor.execute("DROP INDEX IF EXISTS idx_task_events_task_id")
        cursor.execute("DROP INDEX IF EXISTS idx_task_events_event_type")
        cursor.execute("DROP INDEX IF EXISTS idx_task_events_created_at")
        cursor.execute("DROP INDEX IF EXISTS idx_task_events_task_id_type")
        cursor.execute("DROP INDEX IF EXISTS idx_task_events_dedup_key")

        # Drop table
        if table_exists(cursor, "task_events"):
            cursor.execute("DROP TABLE IF EXISTS task_events")
            dropped = True

        # Record migration
        record_migration(cursor, "drop_task_events")

    return dropped
