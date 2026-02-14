"""Shared fixtures for BDD tests.

This conftest.py provides the bdd_db fixture that all BDD step files use.

Note: This module uses `bdd_db` instead of `db_path` to avoid shadowing
the `db_path` fixture in tests/fixtures/database.py. Both fixtures
serve similar purposes but `bdd_db` uses generator pattern with explicit
cleanup while the shared `db_path` uses pytest's tmp_path.
"""

import os
import sqlite3
import tempfile

import pytest

from tests.fixtures.paths import SCHEMA_FILE


def _load_schema_for_tests() -> str:
    """Load schema SQL for tests.

    Schema no longer contains WAL pragma (handled by db_connection.py).
    Uses SCHEMA_FILE from tests.fixtures.paths (Task #2652).
    """
    with open(SCHEMA_FILE) as f:
        return f.read()


@pytest.fixture
def bdd_db():
    """Create a temporary database for BDD tests.

    This fixture:
    1. Loads schema (WAL mode handled by db_connection.py at runtime)
    2. Pre-populates schema_migrations to prevent re-running migrations
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Load schema from packaged location (Task #2652)
    schema_sql = _load_schema_for_tests()

    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_sql)

        # Create migrations tracking table and mark all migrations as applied
        # This prevents re-running migrations that are already incorporated
        # into the base schema
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)

        # Task #2654: SQL migrations removed - schema_migrations table left empty
        # since base schema is always current and no migrations to track
        conn.commit()

    yield db_path

    # Cleanup
    os.unlink(db_path)
