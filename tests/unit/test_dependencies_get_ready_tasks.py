"""Tests for dependencies.get_ready_tasks() function.

Task #2752: Tests for view-based dependency checking.
"""

import sqlite3

from formaltask.tasks.dependencies import get_ready_tasks


class TestGetReadyTasksLogic:
    """Logic tests for get_ready_tasks - behavior verification."""

    def test_task_with_no_dependencies_is_ready(self, db_path: str):
        """Task with no dependencies should be returned as ready."""
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test", "2025-01-01T00:00:00Z"),
            )
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (1, "test-epic", "Independent task", "No deps", "open", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

        ready = get_ready_tasks(db_path, "test-epic")
        assert 1 in ready

    def test_task_with_completed_dependency_is_ready(self, db_path: str):
        """Task with completed dependency should be returned as ready."""
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test", "2025-01-01T00:00:00Z"),
            )
            # Dependency task - completed
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (1, "test-epic", "Done task", "Completed", "completed", "2025-01-01T00:00:00Z"),
            )
            # Dependent task
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, depends_on, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    2,
                    "test-epic",
                    "Main task",
                    "Depends on 1",
                    "open",
                    "[1]",
                    "2025-01-01T00:00:00Z",
                ),
            )
            conn.commit()

        ready = get_ready_tasks(db_path, "test-epic")
        assert 2 in ready

    def test_task_with_cancelled_dependency_is_ready(self, db_path: str):
        """Task with cancelled dependency should be returned as ready.

        Task #2750: Cancelled tasks satisfy dependencies.
        """
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test", "2025-01-01T00:00:00Z"),
            )
            # Dependency task - cancelled
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    1,
                    "test-epic",
                    "Cancelled task",
                    "Was cancelled",
                    "cancelled",
                    "2025-01-01T00:00:00Z",
                ),
            )
            # Dependent task
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, depends_on, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    2,
                    "test-epic",
                    "Main task",
                    "Depends on cancelled",
                    "open",
                    "[1]",
                    "2025-01-01T00:00:00Z",
                ),
            )
            conn.commit()

        ready = get_ready_tasks(db_path, "test-epic")
        # Should include task 2 - cancelled satisfies dependency
        assert 2 in ready

    def test_task_with_open_dependency_not_ready(self, db_path: str):
        """Task with open (incomplete) dependency should NOT be returned as ready."""
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test", "2025-01-01T00:00:00Z"),
            )
            # Dependency task - still open (blocking)
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (1, "test-epic", "Blocking task", "Still open", "open", "2025-01-01T00:00:00Z"),
            )
            # Dependent task
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, depends_on, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    2,
                    "test-epic",
                    "Blocked task",
                    "Depends on 1",
                    "open",
                    "[1]",
                    "2025-01-01T00:00:00Z",
                ),
            )
            conn.commit()

        ready = get_ready_tasks(db_path, "test-epic")
        # Task 1 is ready (no deps), Task 2 is blocked
        assert 1 in ready
        assert 2 not in ready

    def test_filters_by_epic_name(self, db_path: str):
        """get_ready_tasks should only return tasks for the specified epic."""
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("epic-a", "Epic A", "2025-01-01T00:00:00Z"),
            )
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("epic-b", "Epic B", "2025-01-01T00:00:00Z"),
            )
            # Task in epic-a
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (1, "epic-a", "Task in A", "Desc", "open", "2025-01-01T00:00:00Z"),
            )
            # Task in epic-b
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (2, "epic-b", "Task in B", "Desc", "open", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

        ready_a = get_ready_tasks(db_path, "epic-a")
        ready_b = get_ready_tasks(db_path, "epic-b")

        assert 1 in ready_a
        assert 2 not in ready_a
        assert 2 in ready_b
        assert 1 not in ready_b
