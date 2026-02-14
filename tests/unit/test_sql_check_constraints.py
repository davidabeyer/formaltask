"""Tests for SQL CHECK constraints on JSON fields.

Validates Layer 2 (database-level) validation works independently
of Layer 1 (Pydantic) validation.
"""

import sqlite3

import pytest

# Note: db_path fixture is provided by hooks/tests/conftest.py


@pytest.fixture
def conn(db_path):
    """Provide database connection."""
    with sqlite3.connect(db_path) as connection:
        yield connection


def test_tasks_metadata_rejects_invalid_json(conn):
    """Verify CHECK constraint rejects invalid JSON in tasks.metadata."""
    cursor = conn.cursor()

    # Attempt to insert invalid JSON - should raise IntegrityError
    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint"):
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "master-adhoc",
                "Test Task",
                "Description",
                "open",
                1,
                "2025-01-01T00:00:00Z",
                '{"bad": }',
            ),
        )


def test_tasks_metadata_allows_null(conn):
    """Verify NULL is allowed for tasks.metadata."""
    cursor = conn.cursor()

    # Insert with NULL metadata - should succeed
    cursor.execute(
        "INSERT INTO tasks (epic_name, title, description, status, position, created_at, metadata) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("master-adhoc", "Test Task 3", "Description", "open", 1, "2025-01-01T00:00:00Z", None),
    )
    conn.commit()

    # Verify it was inserted
    cursor.execute("SELECT metadata FROM tasks WHERE title = ?", ("Test Task 3",))
    result = cursor.fetchone()
    assert result[0] is None, "NULL should be allowed for metadata"
