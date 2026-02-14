"""Tests for DatabaseConnection context manager."""

from formaltask.db.connection import DatabaseConnection


class TestDatabaseConnection:
    """Tests for DatabaseConnection context manager."""

    def test_busy_timeout_is_set(self, tmp_path):
        """Test that busy_timeout PRAGMA is set to 5000ms.

        This ensures concurrent connections wait up to 5 seconds
        before returning SQLITE_BUSY errors, allowing transient
        lock contention to resolve automatically.
        """
        db_path = tmp_path / "test.db"

        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute("PRAGMA busy_timeout")
            timeout = cursor.fetchone()[0]
            assert timeout == 5000, f"Expected busy_timeout=5000, got {timeout}"
