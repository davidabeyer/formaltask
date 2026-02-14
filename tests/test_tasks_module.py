"""Tests for formaltask.tasks module (Task #2724).

Tests task CRUD operations with db_path-first function signatures.
Uses TDD workflow: RED (failing test) -> GREEN (minimal implementation) -> REFACTOR.
"""

import sqlite3

import pytest


class TestGetTask:
    """Tests for get_task() function."""

    def test_get_task_returns_task_data_when_exists(self, db_with_epic_and_tasks):
        """get_task returns TaskData dict when task exists."""
        from formaltask.tasks import get_task

        result = get_task(db_with_epic_and_tasks, 1)

        assert result is not None
        assert result["id"] == 1
        assert result["title"] == "Task 1"
        assert result["status"] == "open"
        assert result["epic_name"] == "test-epic"

    def test_get_task_returns_none_when_not_found(self, db_path):
        """get_task returns None for non-existent task ID."""
        from formaltask.tasks import get_task

        result = get_task(db_path, 9999)

        assert result is None


class TestCreateTask:
    """Tests for create_task() function."""

    def test_create_task_returns_task_id(self, db_path):
        """create_task returns the new task ID."""
        from formaltask.tasks import create_task

        # First create an epic for the task
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

        task_id = create_task(
            db_path,
            epic_name="test-epic",
            title="Test Task",
            description="A test task",
            criteria=["Criterion 1", "Criterion 2"],
        )

        assert isinstance(task_id, int)
        assert task_id > 0

    def test_create_task_stores_task_in_database(self, db_path):
        """create_task stores the task with correct values."""
        from formaltask.tasks import create_task, get_task

        # Create epic
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

        task_id = create_task(
            db_path,
            epic_name="test-epic",
            title="My Task",
            description="Description here",
            criteria=["Must work"],
        )

        # Verify stored values
        task = get_task(db_path, task_id)
        assert task is not None
        assert task["title"] == "My Task"
        assert task["description"] == "Description here"
        assert task["status"] == "open"

    def test_create_task_raises_on_missing_epic(self, db_path):
        """create_task raises EpicNotFoundError for non-existent epic."""
        from formaltask.exceptions import EpicNotFoundError
        from formaltask.tasks import create_task

        with pytest.raises(EpicNotFoundError):
            create_task(
                db_path,
                epic_name="nonexistent-epic",
                title="Test",
                description="Test",
                criteria=["Test"],
            )


class TestStartTask:
    """Tests for transition_task_status() to in_progress."""

    def test_start_task_transitions_to_in_progress(self, db_with_epic_and_tasks):
        """transition_task_status transitions task status to in_progress."""
        from formaltask.tasks import get_task, transition_task_status

        # Task 1 is open in the fixture
        transition_task_status(db_with_epic_and_tasks, 1, "in_progress")

        task = get_task(db_with_epic_and_tasks, 1)
        assert task is not None
        assert task["status"] == "in_progress"
        assert task["started_at"] is not None

    def test_start_task_raises_on_invalid_task(self, db_path):
        """transition_task_status raises TaskNotFoundError for non-existent task."""
        from formaltask.exceptions import TaskNotFoundError
        from formaltask.tasks import transition_task_status

        with pytest.raises(TaskNotFoundError):
            transition_task_status(db_path, 9999, "in_progress")


class TestCompleteTask:
    """Tests for transition_task_status() to completed."""

    def test_complete_task_transitions_to_completed(self, db_with_epic_and_tasks):
        """transition_task_status transitions task status to completed."""
        from formaltask.tasks import get_task, transition_task_status

        # Start task first (need to be in_progress to complete)
        transition_task_status(db_with_epic_and_tasks, 1, "in_progress")

        transition_task_status(db_with_epic_and_tasks, 1, "completed")

        task = get_task(db_with_epic_and_tasks, 1)
        assert task is not None
        assert task["status"] == "completed"
        assert task["completed_at"] is not None


class TestGetTasks:
    """Tests for get_tasks() function."""

    def test_get_tasks_returns_list_of_tasks(self, db_with_epic_and_tasks):
        """get_tasks returns list of TaskListItem dicts."""
        from formaltask.tasks import get_tasks

        tasks = get_tasks(db_with_epic_and_tasks, "test-epic")

        assert isinstance(tasks, list)
        assert len(tasks) == 5
        assert tasks[0]["id"] == 1
        assert tasks[0]["title"] == "Task 1"
        assert tasks[0]["status"] == "open"

    def test_get_tasks_returns_empty_for_unknown_epic(self, db_path):
        """get_tasks returns empty list for non-existent epic."""
        from formaltask.tasks import get_tasks

        tasks = get_tasks(db_path, "nonexistent-epic")

        assert tasks == []


class TestGetInProgressTasks:
    """Tests for get_in_progress_tasks() function."""

    def test_get_in_progress_tasks_returns_task_ids(self, db_with_epic_and_tasks):
        """get_in_progress_tasks returns list of task IDs in in_progress status."""
        from formaltask.tasks import get_in_progress_tasks

        # Fixture has task 3 in_progress
        result = get_in_progress_tasks(db_with_epic_and_tasks, "test-epic")

        assert isinstance(result, list)
        assert 3 in result

    def test_get_in_progress_tasks_returns_empty_when_none(self, db_path):
        """get_in_progress_tasks returns empty list when no tasks in_progress."""
        from formaltask.tasks import get_in_progress_tasks

        result = get_in_progress_tasks(db_path, "test-epic")

        assert result == []


class TestCreateTasksBatch:
    """Tests for create_tasks_batch() function."""

    def test_create_tasks_batch_returns_task_ids(self, db_path):
        """create_tasks_batch returns list of created task IDs."""
        from formaltask.tasks import create_tasks_batch

        # Create epic
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

        tasks_data = [
            {"title": "Task 1", "description": "Desc 1", "criteria": ["C1"]},
            {"title": "Task 2", "description": "Desc 2", "criteria": ["C2"]},
        ]

        task_ids = create_tasks_batch(db_path, "test-epic", tasks_data)

        assert isinstance(task_ids, list)
        assert len(task_ids) == 2
        assert all(isinstance(tid, int) for tid in task_ids)

    def test_create_tasks_batch_empty_list_returns_empty(self, db_path):
        """create_tasks_batch returns empty list for empty input."""
        from formaltask.tasks import create_tasks_batch

        result = create_tasks_batch(db_path, "test-epic", [])

        assert result == []


class TestDeferTask:
    """Tests for defer_task() function."""

    def test_defer_task_transitions_to_deferred(self, db_with_epic_and_tasks):
        """defer_task transitions task status to deferred."""
        from formaltask.tasks import defer_task, get_task, transition_task_status

        # Start task first (can defer from in_progress)
        transition_task_status(db_with_epic_and_tasks, 1, "in_progress")

        # Reason must be at least 20 characters per validation
        defer_task(db_with_epic_and_tasks, 1, "Need more info to proceed with this task")

        task = get_task(db_with_epic_and_tasks, 1)
        assert task is not None
        assert task["status"] == "deferred"

    def test_defer_task_raises_on_short_reason(self, db_with_epic_and_tasks):
        """defer_task raises ValueError when reason is too short."""
        from formaltask.tasks import defer_task, transition_task_status

        transition_task_status(db_with_epic_and_tasks, 1, "in_progress")

        with pytest.raises(ValueError, match="at least 20 characters"):
            defer_task(db_with_epic_and_tasks, 1, "Too short")


class TestDeleteTaskVerified:
    """Tests for delete_task_verified() function."""

    def test_delete_task_verified_removes_task(self, db_with_epic_and_tasks):
        """delete_task_verified removes task from database."""
        from formaltask.tasks import delete_task_verified, get_task

        result = delete_task_verified(db_with_epic_and_tasks, 1)

        assert result is True
        assert get_task(db_with_epic_and_tasks, 1) is None

    def test_delete_task_verified_returns_false_for_nonexistent(self, db_path):
        """delete_task_verified returns False for non-existent task."""
        from formaltask.tasks import delete_task_verified

        result = delete_task_verified(db_path, 9999)

        assert result is False


class TestLinkCommit:
    """Tests for linking commits to tasks via inline SQL."""

    def test_link_commit_stores_commit_reference(self, db_with_epic_and_tasks):
        """Inline SQL stores commit reference in database."""
        from formaltask.db.connection import DatabaseConnection

        with DatabaseConnection(db_with_epic_and_tasks) as conn:
            conn.cursor().execute(
                "INSERT OR IGNORE INTO commits (task_id, commit_hash, commit_message) VALUES (?, ?, ?)",
                (1, "abc123", "Fix bug"),
            )
            conn.commit()

        # Verify commit was stored
        with sqlite3.connect(db_with_epic_and_tasks) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT commit_hash, commit_message FROM commits WHERE task_id = ?",
                (1,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "abc123"
        assert row[1] == "Fix bug"
