"""Consolidated schema migration - adds missing columns idempotently (Task #2684).

Replaces 43 individual migration files with a single ensure_schema.py.
All columns listed in ENSURE_COLUMNS are added if they don't exist.
Fresh databases (created from schema.sql) already have these columns,
so this is a no-op for them. Old databases get missing columns added.

No classes, no wrappers, plain functions only.
"""

from formaltask.db.connection import DatabaseConnection
from formaltask.db.migrations.helpers import column_exists, record_migration, table_exists

# All columns that need to exist (table, column, sql_definition)
# Skip workers table - it was dropped by drop_workers_table.py
ENSURE_COLUMNS = [
    # tasks table
    ("tasks", "blocked_question", "TEXT"),
    ("tasks", "completion_evidence", "TEXT"),
    ("tasks", "defer_reason", "TEXT"),  # CHECK constraint in schema.sql only
    ("tasks", "cancel_reason", "TEXT"),
    ("tasks", "cancelled_at", "TEXT"),
    ("tasks", "session_id", "TEXT"),
    ("tasks", "review_round", "INTEGER"),
    ("tasks", "pr_url", "TEXT"),
    ("tasks", "artifact_type", "TEXT"),
    # epics table
    ("epics", "feature_branch", "TEXT"),
    ("epics", "reviewed_at", "TEXT"),
    # task_reviews table
    ("task_reviews", "round", "INTEGER DEFAULT 1"),
    # planning_state table
    ("planning_state", "plan_file_path", "TEXT"),
    # acceptance_criteria table (Task #2859: runnable AC)
    ("acceptance_criteria", "command", "TEXT"),
]


def migrate(db_path: str) -> bool:
    """Ensure all required columns exist in database tables.

    Idempotent operation - safe to run multiple times. Returns True if
    any columns were added, False if all columns already existed.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        True if at least one column was added, False otherwise.
    """
    columns_added = 0

    with DatabaseConnection(str(db_path)) as conn:
        cursor = conn.cursor()

        for table, column, definition in ENSURE_COLUMNS:
            # Skip if table doesn't exist
            if not table_exists(cursor, table):
                continue

            # Skip if column already exists
            if column_exists(cursor, table, column):
                continue

            # Add the column (ALTER TABLE is atomic in SQLite, no explicit transaction needed)
            # Safe: table validated by column_exists against VALID_TABLES allowlist,
            # column/definition from hardcoded ENSURE_COLUMNS
            # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
            cursor.execute(  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query
                f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
            )
            columns_added += 1

        # Record migration if we added anything
        if columns_added > 0:
            record_migration(cursor, "ensure_schema")

    return columns_added > 0
