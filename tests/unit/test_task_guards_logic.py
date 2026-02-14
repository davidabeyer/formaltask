"""Logic tests for TaskGuards.check_dependencies_satisfied().

Task #2752: Tests for view-based dependency checking. The function should:
- Pass if task has no dependencies
- Pass if all dependencies are completed
- Pass if all dependencies are cancelled (cancelled satisfies dependency)
- Raise GuardViolation if any dependency is open/in_progress
"""

import sqlite3

import pytest

from formaltask.tasks.guards import GuardViolation, TaskGuards


class TestCheckDependenciesSatisfiedLogic:
    """Logic tests for check_dependencies_satisfied - behavior, not error formatting."""

    def test_task_with_no_dependencies_passes(self, db_path: str):
        """Task with no dependencies should pass the guard."""
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

        guards = TaskGuards(db_path)
        # Should not raise
        guards.check_dependencies_satisfied(1)

    def test_task_with_completed_dependency_passes(self, db_path: str):
        """Task with completed dependency should pass the guard."""
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test", "2025-01-01T00:00:00Z"),
            )
            # Dependency task - completed
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (1, "test-epic", "Dep task", "Dependency", "completed", "2025-01-01T00:00:00Z"),
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

        guards = TaskGuards(db_path)
        # Should not raise
        guards.check_dependencies_satisfied(2)

    def test_task_with_cancelled_dependency_passes(self, db_path: str):
        """Task with cancelled dependency should pass - cancelled satisfies dependency.

        Task #2750: Cancelled tasks don't block dependents.
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

        guards = TaskGuards(db_path)
        # Should not raise - cancelled satisfies dependency
        guards.check_dependencies_satisfied(2)

    def test_task_with_open_dependency_raises(self, db_path: str):
        """Task with open dependency should raise GuardViolation."""
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test", "2025-01-01T00:00:00Z"),
            )
            # Dependency task - open (blocking)
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

        guards = TaskGuards(db_path)
        with pytest.raises(GuardViolation):
            guards.check_dependencies_satisfied(2)

    def test_task_with_in_progress_dependency_raises(self, db_path: str):
        """Task with in_progress dependency should raise GuardViolation."""
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test", "2025-01-01T00:00:00Z"),
            )
            # Dependency task - in_progress (blocking)
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    1,
                    "test-epic",
                    "In progress task",
                    "Being worked on",
                    "in_progress",
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
                    "Blocked task",
                    "Depends on 1",
                    "open",
                    "[1]",
                    "2025-01-01T00:00:00Z",
                ),
            )
            conn.commit()

        guards = TaskGuards(db_path)
        with pytest.raises(GuardViolation):
            guards.check_dependencies_satisfied(2)

    def test_task_with_mixed_dependencies_blocks_on_incomplete(self, db_path: str):
        """Task with some completed and some open dependencies should raise GuardViolation."""
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test", "2025-01-01T00:00:00Z"),
            )
            # Dependency 1 - completed (satisfied)
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (1, "test-epic", "Done task", "Completed", "completed", "2025-01-01T00:00:00Z"),
            )
            # Dependency 2 - open (blocking)
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (2, "test-epic", "Open task", "Still open", "open", "2025-01-01T00:00:00Z"),
            )
            # Dependent task
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, depends_on, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    3,
                    "test-epic",
                    "Blocked task",
                    "Depends on both",
                    "open",
                    "[1, 2]",
                    "2025-01-01T00:00:00Z",
                ),
            )
            conn.commit()

        guards = TaskGuards(db_path)
        with pytest.raises(GuardViolation):
            guards.check_dependencies_satisfied(3)
