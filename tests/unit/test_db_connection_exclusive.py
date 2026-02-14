"""Test DatabaseConnection exclusive transaction mode.

Tests for the exclusive=True parameter that provides EXCLUSIVE isolation
for preventing race conditions in Greptile review worker operations.
"""

import sqlite3

import pytest


class TestDatabaseConnectionExclusive:
    """Test exclusive transaction mode for DatabaseConnection."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database for testing."""
        db_path = tmp_path / "test.db"
        # Initialize with a simple table
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, value TEXT)")
            conn.execute("INSERT INTO test_data VALUES (1, 'initial')")
            conn.commit()
        return str(db_path)

    def test_exclusive_mode_acquires_exclusive_lock(self, temp_db):
        """When exclusive=True, connection should acquire EXCLUSIVE lock.

        This prevents other connections from reading or writing while
        the exclusive transaction is active.
        """
        from formaltask.db.connection import DatabaseConnection

        # Start exclusive transaction
        with DatabaseConnection(temp_db, exclusive=True) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE test_data SET value = 'updated' WHERE id = 1")

            # Another connection should be blocked from writing
            # (EXCLUSIVE lock blocks all other connections)
            # Use 2s timeout for CI reliability (Task #697) - still fast enough to fail
            # quickly if lock isn't held, but avoids false failures on slow CI
            with (
                sqlite3.connect(temp_db, timeout=2.0) as other_conn,
                pytest.raises(sqlite3.OperationalError, match="database is locked"),
            ):
                other_conn.execute("UPDATE test_data SET value = 'other' WHERE id = 1")

        # After exiting, changes should be committed
        with sqlite3.connect(temp_db) as verify_conn:
            cursor = verify_conn.cursor()
            cursor.execute("SELECT value FROM test_data WHERE id = 1")
            assert cursor.fetchone()[0] == "updated"

    def test_exclusive_mode_rollback_on_exception(self, temp_db):
        """When exception occurs in exclusive mode, changes should be rolled back.

        Task #630: Test error case for database transactions.
        """
        from formaltask.db.connection import DatabaseConnection

        # Attempt transaction that raises exception
        with (
            pytest.raises(ValueError, match="Intentional"),
            DatabaseConnection(temp_db, exclusive=True) as conn,
        ):
            cursor = conn.cursor()
            cursor.execute("UPDATE test_data SET value = 'should_rollback' WHERE id = 1")
            raise ValueError("Intentional error")

        # Changes should be rolled back
        with sqlite3.connect(temp_db) as verify_conn:
            cursor = verify_conn.cursor()
            cursor.execute("SELECT value FROM test_data WHERE id = 1")
            assert cursor.fetchone()[0] == "initial", "Changes should be rolled back on exception"
