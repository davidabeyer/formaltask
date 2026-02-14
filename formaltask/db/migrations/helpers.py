"""Shared helper functions for migration scripts."""

import sqlite3


def table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    """Check if table exists in database."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cursor.fetchone() is not None


VALID_TABLES = frozenset(
    {
        "workers",
        "tasks",
        "epics",
        "reviews",
        "schema_migrations",
        "automated_reviews",
        "task_reviews",  # renamed from automated_reviews (Task #1883)
        "planning_state",  # Added for Task #2367 - plan_file_path column
        "acceptance_criteria",  # Added for Task #2859 - runnable AC command column
        # task_reflections removed (Task #2759 - dead code, never wired up)
        # pending_decisions removed (Task #2150 - dropped @@@NEEDS_HUMAN infrastructure)
        # plan_documents removed (Task #2248 - dropped ceremony tables)
        # critique_findings removed (Task #2248 - dropped ceremony tables)
    }
)


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """Check if column exists in table."""
    if table not in VALID_TABLES:
        raise ValueError(f"Invalid table name: {table}")
    # Safe: table is validated against VALID_TABLES allowlist (defined above)
    # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
    cursor.execute(  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query
        f"PRAGMA table_info({table})"
    )
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def migration_applied(cursor: sqlite3.Cursor, migration_name: str) -> bool:
    """Check if a migration has already been applied."""
    if not table_exists(cursor, "schema_migrations"):
        return False
    cursor.execute(
        "SELECT 1 FROM schema_migrations WHERE name = ?",
        (migration_name,),
    )
    return cursor.fetchone() is not None


def record_migration(cursor: sqlite3.Cursor, migration_name: str) -> None:
    """Record a migration as applied in schema_migrations.

    Uses INSERT OR IGNORE for idempotency - safe to call multiple times.
    """
    if table_exists(cursor, "schema_migrations"):
        cursor.execute(
            "INSERT OR IGNORE INTO schema_migrations (name, applied_at) VALUES (?, datetime('now'))",
            (migration_name,),
        )
