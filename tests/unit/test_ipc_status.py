"""Tests for IPC status values and state machine transitions.

Task #1279: Add PENDING_REVIEW and BLOCKED_USER to TaskStatus enum.

TDD RED Phase: These tests are written BEFORE implementation.
"""

import pytest


class TestValidTransitionsDict:
    """Test VALID_TRANSITIONS dict enforces state machine."""

    def test_valid_transitions_in_progress_to_pending_review(self):
        """IN_PROGRESS must allow transition to PENDING_REVIEW."""
        from formaltask.tasks.lifecycle import VALID_TRANSITIONS
        from formaltask.utils.constants import TaskStatus

        assert TaskStatus.PENDING_REVIEW in VALID_TRANSITIONS[TaskStatus.IN_PROGRESS]

    def test_valid_transitions_in_progress_to_blocked_user(self):
        """IN_PROGRESS must allow transition to BLOCKED_USER."""
        from formaltask.tasks.lifecycle import VALID_TRANSITIONS
        from formaltask.utils.constants import TaskStatus

        assert TaskStatus.BLOCKED_USER in VALID_TRANSITIONS[TaskStatus.IN_PROGRESS]

    def test_valid_transitions_has_all_statuses(self):
        """Every TaskStatus must have an entry in VALID_TRANSITIONS."""
        from formaltask.tasks.lifecycle import VALID_TRANSITIONS
        from formaltask.utils.constants import TaskStatus

        for status in TaskStatus:
            assert status in VALID_TRANSITIONS, f"Missing VALID_TRANSITIONS entry for {status}"


class TestTransitionValidation:
    """Test transition_task_status validates transitions using VALID_TRANSITIONS."""

    @pytest.fixture
    def test_db(self, tmp_path):
        """Create a test database with tasks table."""
        import sqlite3

        db_path = tmp_path / "test.db"
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()

            # Create minimal schema for testing
            cursor.execute("""
                CREATE TABLE epics (
                    name TEXT PRIMARY KEY,
                    description TEXT,
                    status TEXT DEFAULT 'open',
                    created_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    epic_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    started_at TEXT,
                    completed_at TEXT,
                    created_at TEXT NOT NULL,
                    head_commit_sha TEXT,
                    FOREIGN KEY (epic_name) REFERENCES epics(name)
                )
            """)
            cursor.execute(
                "INSERT INTO epics (name, description, status, created_at) VALUES (?, ?, ?, ?)",
                ("test-epic", "Test epic", "open", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

        return db_path

    def _create_task(self, db_path, status: str = "open") -> int:
        """Helper to create a task with given status."""
        import sqlite3

        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tasks (epic_name, title, description, status, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("test-epic", "Test task", "Test description", status, "2025-01-01T00:00:00Z"),
            )
            task_id = cursor.lastrowid
            conn.commit()
            return task_id

    def test_invalid_transition_raises_error(self, test_db):
        """Transition from OPEN directly to COMPLETED must raise InvalidTransitionError."""
        from formaltask.tasks.lifecycle import InvalidTransitionError, transition_task_status

        task_id = self._create_task(test_db, status="open")

        with pytest.raises(InvalidTransitionError):
            transition_task_status(test_db, task_id, "completed")

    def test_transition_pending_review_to_completed(self, test_db):
        """Transition from PENDING_REVIEW to COMPLETED must succeed."""
        from formaltask.tasks.lifecycle import transition_task_status

        task_id = self._create_task(test_db, status="pending_review")

        result = transition_task_status(test_db, task_id, "completed")
        assert result is True

    def test_transition_blocked_user_to_in_progress(self, test_db):
        """Transition from BLOCKED_USER to IN_PROGRESS must succeed."""
        from formaltask.tasks.lifecycle import transition_task_status

        task_id = self._create_task(test_db, status="blocked_user")

        result = transition_task_status(test_db, task_id, "in_progress")
        assert result is True

    def test_valid_transition_blocked_user_to_completed(self, test_db):
        """BLOCKED_USER can transition directly to COMPLETED (allows ft task-complete on blocked tasks)."""
        from formaltask.tasks.lifecycle import transition_task_status

        task_id = self._create_task(test_db, status="blocked_user")
        transition_task_status(test_db, task_id, "completed")
        # Should not raise - transition is now allowed

    def test_invalid_transition_from_terminal_completed(self, test_db):
        """COMPLETED is terminal - cannot transition to any other status."""
        from formaltask.tasks.lifecycle import InvalidTransitionError, transition_task_status

        task_id = self._create_task(test_db, status="completed")

        with pytest.raises(InvalidTransitionError):
            transition_task_status(test_db, task_id, "open")

    def test_invalid_transition_from_terminal_cancelled(self, test_db):
        """CANCELLED is terminal - cannot transition to any other status."""
        from formaltask.tasks.lifecycle import InvalidTransitionError, transition_task_status

        task_id = self._create_task(test_db, status="cancelled")

        with pytest.raises(InvalidTransitionError):
            transition_task_status(test_db, task_id, "open")


# Note: TestTaskQuestionsTable class removed in Task #2654 - SQL migrations deleted
# task_questions table is now defined in formaltask/data/schema.sql
