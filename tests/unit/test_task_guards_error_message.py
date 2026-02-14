"""Unit tests for task_guards.py.

Tests for TaskGuards dependency checking, particularly error message formatting.
"""

import pytest

from formaltask.tasks.guards import GuardViolation, TaskGuards


class TestCheckDependenciesSatisfiedErrorMessage:
    """Tests for error message formatting in check_dependencies_satisfied."""

    def test_error_message_shows_task_titles(self, db_path, repo):
        """Error message for incomplete dependencies includes task titles.

        Expected format: "Task #3 blocked - dependencies not completed: #1 (Fix auth), #2 (Add tests)"
        """
        # Setup: Create two incomplete dependency tasks and one task that depends on them
        repo.create_epic("test-epic", "Test epic")

        # Dependency task 1 - open (not completed)
        task1_id = repo.create_task(
            "test-epic", "Fix authentication bug", "Fix auth", ["criterion"]
        )

        # Dependency task 2 - open (not completed)
        task2_id = repo.create_task("test-epic", "Add unit tests", "Add tests", ["criterion"])

        # Task 3 depends on tasks 1 and 2
        task3_id = repo.create_task(
            "test-epic", "Main feature", "Main", ["criterion"], depends_on=[task1_id, task2_id]
        )

        # Act & Assert
        guards = TaskGuards(db_path)

        with pytest.raises(GuardViolation) as exc_info:
            guards.check_dependencies_satisfied(task3_id)

        error_message = str(exc_info.value)

        # Verify error message contains task IDs with titles
        assert f"#{task1_id} (Fix authentication bug)" in error_message, (
            f"Expected '#{task1_id} (Fix authentication bug)' in error message: {error_message}"
        )
        assert f"#{task2_id} (Add unit tests)" in error_message, (
            f"Expected '#{task2_id} (Add unit tests)' in error message: {error_message}"
        )
