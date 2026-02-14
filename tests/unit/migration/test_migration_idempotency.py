"""Test that migrations are idempotent and don't reset data.

This test verifies that calling ensure_schema_initialized multiple times
doesn't cause data loss - migrations should only run once.
"""

import pytest

from formaltask.db.connection import DatabaseConnection
from formaltask.db.schema import ensure_schema_initialized


class TestMigrationIdempotency:
    """Test that migrations only run once and don't reset data."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database for testing."""
        db_path = tmp_path / "test.db"
        return str(db_path)

    def test_depends_on_persists_across_schema_init_calls(self, temp_db):
        """depends_on values should persist when calling ensure_schema_initialized again.

        Verifies that migrations are idempotent - calling ensure_schema_initialized
        multiple times should not reset the database or lose data.
        """
        # Initialize schema first time
        ensure_schema_initialized(temp_db)

        # Create test data
        with DatabaseConnection(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
            )
            cursor.execute(
                """INSERT INTO tasks (epic_name, title, description, position, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("test-epic", "Task 1", "First task", 0, "open", "2025-01-01T00:00:00Z"),
            )
            task1_id = cursor.lastrowid
            cursor.execute(
                """INSERT INTO tasks (epic_name, title, description, position, status, created_at, depends_on)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    "test-epic",
                    "Task 2",
                    "Second task",
                    1,
                    "open",
                    "2025-01-01T00:00:00Z",
                    f"[{task1_id}]",
                ),
            )
            task2_id = cursor.lastrowid
            conn.commit()

        # Verify dependency was set
        with DatabaseConnection(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT depends_on FROM tasks WHERE id = ?", (task2_id,))
            result = cursor.fetchone()
            assert result[0] == f"[{task1_id}]", "Dependency should be set"

        # Call ensure_schema_initialized again (should NOT reset data)
        ensure_schema_initialized(temp_db)

        # Verify dependency persists
        with DatabaseConnection(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT depends_on FROM tasks WHERE id = ?", (task2_id,))
            result = cursor.fetchone()
            assert result[0] == f"[{task1_id}]", (
                "depends_on should persist across ensure_schema_initialized calls. "
                "Bug: migrations are running on every init and resetting the table."
            )
