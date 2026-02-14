"""Test SQL views for derived task state.

Tests for views that derive task state from authoritative tables:
- task_ready_status: Tasks ready to start (open + all deps completed)
"""

import sqlite3


class TestTaskReadyStatusView:
    """Tests for task_ready_status view."""

    def test_view_exists(self, db_path):
        """View should exist after schema initialization."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='view' AND name='task_ready_status'"
            )
            result = cursor.fetchone()
            assert result is not None, "task_ready_status view should exist"

    def test_task_with_no_dependencies_is_ready(self, db_path):
        """Open task with no dependencies should appear in ready view."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # Create epic and task with no dependencies
            cursor.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, datetime('now'))",
                ("test-epic", "Test epic"),
            )
            cursor.execute(
                """INSERT INTO tasks (epic_name, title, description, status, created_at, depends_on)
                   VALUES (?, ?, ?, 'open', datetime('now'), '[]')""",
                ("test-epic", "Test task", "Description"),
            )
            task_id = cursor.lastrowid
            conn.commit()

            # Query view
            cursor.execute("SELECT task_id FROM task_ready_status WHERE task_id = ?", (task_id,))
            result = cursor.fetchone()
            assert result is not None, "Task with no deps should be in ready view"

    def test_task_with_completed_dependencies_is_ready(self, db_path):
        """Open task with all completed dependencies should appear in ready view."""
        import json

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, datetime('now'))",
                ("test-epic", "Test epic"),
            )
            # Create dependency task (completed)
            cursor.execute(
                """INSERT INTO tasks (epic_name, title, description, status, created_at, completed_at, depends_on)
                   VALUES (?, ?, ?, 'completed', datetime('now'), datetime('now'), '[]')""",
                ("test-epic", "Dep task", "Description"),
            )
            dep_task_id = cursor.lastrowid

            # Create task that depends on completed task
            cursor.execute(
                """INSERT INTO tasks (epic_name, title, description, status, created_at, depends_on)
                   VALUES (?, ?, ?, 'open', datetime('now'), ?)""",
                ("test-epic", "Dependent task", "Description", json.dumps([dep_task_id])),
            )
            task_id = cursor.lastrowid
            conn.commit()

            cursor.execute("SELECT task_id FROM task_ready_status WHERE task_id = ?", (task_id,))
            result = cursor.fetchone()
            assert result is not None, "Task with completed deps should be in ready view"

    def test_task_with_incomplete_dependencies_not_ready(self, db_path):
        """Open task with incomplete dependencies should NOT appear in ready view."""
        import json

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, datetime('now'))",
                ("test-epic", "Test epic"),
            )
            # Create dependency task (still open)
            cursor.execute(
                """INSERT INTO tasks (epic_name, title, description, status, created_at, depends_on)
                   VALUES (?, ?, ?, 'open', datetime('now'), '[]')""",
                ("test-epic", "Dep task", "Description"),
            )
            dep_task_id = cursor.lastrowid

            # Create task that depends on open task
            cursor.execute(
                """INSERT INTO tasks (epic_name, title, description, status, created_at, depends_on)
                   VALUES (?, ?, ?, 'open', datetime('now'), ?)""",
                ("test-epic", "Dependent task", "Description", json.dumps([dep_task_id])),
            )
            task_id = cursor.lastrowid
            conn.commit()

            cursor.execute("SELECT task_id FROM task_ready_status WHERE task_id = ?", (task_id,))
            result = cursor.fetchone()
            assert result is None, "Task with incomplete deps should NOT be in ready view"

    def test_non_open_task_not_ready(self, db_path):
        """Tasks not in 'open' status should NOT appear in ready view."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, datetime('now'))",
                ("test-epic", "Test epic"),
            )
            # Create in_progress task
            cursor.execute(
                """INSERT INTO tasks (epic_name, title, description, status, created_at, depends_on)
                   VALUES (?, ?, ?, 'in_progress', datetime('now'), '[]')""",
                ("test-epic", "In progress task", "Description"),
            )
            task_id = cursor.lastrowid
            conn.commit()

            cursor.execute("SELECT task_id FROM task_ready_status WHERE task_id = ?", (task_id,))
            result = cursor.fetchone()
            assert result is None, "in_progress task should NOT be in ready view"
