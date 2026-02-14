"""Tests for DatabaseConnection context manager.

Following TDD approach: write tests first, then implement.
"""

import sqlite3

import pytest


def test_database_connection_opens_and_closes_automatically(tmp_path):
    """Test DatabaseConnection context manager opens and closes connection."""
    # Given: A test database path
    from formaltask.db.connection import DatabaseConnection

    db_file = tmp_path / "test.db"

    # When: Using context manager
    with DatabaseConnection(db_file) as conn:
        # Then: Connection is open and usable
        assert conn is not None
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        # DatabaseConnection sets row_factory=sqlite3.Row, so result is a Row object
        assert tuple(result) == (1,)

    # Then: Connection is closed after context exits
    # Attempting to use closed connection should fail
    with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed database"):
        conn.cursor()


# NOTE: Tests for transaction=True parameter were removed (Task #559).
# The parameter was REMOVED because it was stored but NEVER used (always autocommit).
# See test_database_connection_rejects_transaction_parameter for the removal test.
# Repository code now uses explicit BEGIN/COMMIT for transactions.


def test_database_connection_rejects_transaction_parameter(tmp_path):
    """Test that DatabaseConnection no longer accepts transaction parameter.

    The transaction parameter was removed because:
    1. It was stored but NEVER used - always autocommit mode
    2. Misleading API suggesting transactions that didn't happen
    3. Caused confusion when task-complete appeared to succeed but didn't commit

    This is the acceptance criteria test for Task #559.
    """
    from formaltask.db.connection import DatabaseConnection

    db_file = tmp_path / "test.db"

    # Should raise TypeError for unexpected keyword argument
    with pytest.raises(TypeError, match="unexpected keyword argument 'transaction'"):
        DatabaseConnection(db_file, transaction=True)
