"""Test migration for adding command column to acceptance_criteria table.

Task #2859: Add command column to acceptance_criteria for runnable AC support.
"""

import sqlite3

import pytest

from formaltask.db.connection import DatabaseConnection
from formaltask.db.schema import ensure_schema_initialized


class TestAddACCommandColumn:
    """Test that command column is added to acceptance_criteria table."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database for testing."""
        db_path = tmp_path / "test.db"
        return str(db_path)

    def test_schema_creates_command_column_in_acceptance_criteria(self, temp_db):
        """ensure_schema_initialized creates command column in acceptance_criteria table."""
        ensure_schema_initialized(temp_db)

        with DatabaseConnection(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(acceptance_criteria)")
            columns = [row[1] for row in cursor.fetchall()]

        assert "command" in columns, (
            "acceptance_criteria table should have 'command' column after schema init"
        )

    def test_command_column_is_nullable(self, temp_db):
        """command column should be nullable TEXT to support criteria without commands."""
        ensure_schema_initialized(temp_db)

        with DatabaseConnection(temp_db) as conn:
            cursor = conn.cursor()
            # Create test epic and task first
            cursor.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
            )
            cursor.execute(
                """INSERT INTO tasks (epic_name, title, description, position, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("test-epic", "Task 1", "First task", 0, "open", "2025-01-01T00:00:00Z"),
            )
            task_id = cursor.lastrowid

            # Insert criteria with NULL command - should succeed
            cursor.execute(
                """INSERT INTO acceptance_criteria (task_id, text, command)
                   VALUES (?, ?, NULL)""",
                (task_id, "Test criterion"),
            )

            # Insert criteria with command - should also succeed
            cursor.execute(
                """INSERT INTO acceptance_criteria (task_id, text, command)
                   VALUES (?, ?, ?)""",
                (task_id, "Runnable criterion", "pytest tests/"),
            )

            conn.commit()

        # Verify both were inserted correctly
        with DatabaseConnection(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT text, command FROM acceptance_criteria WHERE task_id = ? ORDER BY id",
                (task_id,),
            )
            rows = cursor.fetchall()

        assert len(rows) == 2
        assert rows[0]["text"] == "Test criterion"
        assert rows[0]["command"] is None
        assert rows[1]["text"] == "Runnable criterion"
        assert rows[1]["command"] == "pytest tests/"

    def test_migration_adds_command_column_to_existing_db(self, temp_db):
        """Migration adds command column to existing database without column."""
        # Create a database WITHOUT the command column (simulating old schema)
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE epics (
                    name TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    epic_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT DEFAULT 'open',
                    position INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (epic_name) REFERENCES epics(name)
                )
            """)
            # Old schema: acceptance_criteria WITHOUT command column
            cursor.execute("""
                CREATE TABLE acceptance_criteria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    checked BOOLEAN DEFAULT FALSE,
                    evidence TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)
            cursor.execute("""
                CREATE TABLE schema_migrations (
                    name TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """)
            # Insert existing data
            cursor.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
            )
            cursor.execute(
                """INSERT INTO tasks (epic_name, title, description, position, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("test-epic", "Task 1", "First task", 0, "open", "2025-01-01T00:00:00Z"),
            )
            task_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO acceptance_criteria (task_id, text) VALUES (?, ?)",
                (task_id, "Existing criterion"),
            )
            conn.commit()

        # Verify command column doesn't exist yet
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(acceptance_criteria)")
            columns = [row[1] for row in cursor.fetchall()]
            assert "command" not in columns, "Precondition: command column should not exist"

        # Run migration
        ensure_schema_initialized(temp_db)

        # Verify command column now exists
        with DatabaseConnection(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(acceptance_criteria)")
            columns = [row[1] for row in cursor.fetchall()]

        assert "command" in columns, (
            "command column should be added by migration"
        )

        # Verify existing data preserved with NULL command
        with DatabaseConnection(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT text, command FROM acceptance_criteria WHERE task_id = ?",
                (task_id,),
            )
            row = cursor.fetchone()

        assert row["text"] == "Existing criterion", (
            "Existing criteria text should be preserved after migration"
        )
        assert row["command"] is None, (
            "Existing criteria should have NULL command after migration"
        )
