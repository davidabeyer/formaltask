"""Drop dead infrastructure (Task #2759).

Removes unused tables and records cleanup in schema_migrations.
- task_reflections: 0 rows, never wired up
- created_from_review_of column: left in place (SQLite DROP COLUMN is complex)
"""

from formaltask.db.connection import DatabaseConnection
from formaltask.db.migrations.helpers import migration_applied, record_migration, table_exists


def migrate(db_path: str) -> bool:
    """Drop dead infrastructure from database.

    Idempotent - safe to run multiple times.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        True if anything was dropped, False otherwise.
    """
    with DatabaseConnection(str(db_path)) as conn:
        cursor = conn.cursor()

        # Skip if already applied
        if migration_applied(cursor, "drop_dead_infrastructure"):
            return False

        dropped = False

        # Drop task_reflections if it exists
        if table_exists(cursor, "task_reflections"):
            cursor.execute("DROP TABLE IF EXISTS task_reflections")
            dropped = True

        # Record migration
        record_migration(cursor, "drop_dead_infrastructure")

    return dropped
