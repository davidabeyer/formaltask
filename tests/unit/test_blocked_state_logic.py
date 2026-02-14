"""Tests for blocked state logic using tasks table as single source of truth.

Task #2387: Update pm blocked, inbox, and resume to use tasks.status=blocked_user
and tasks.blocked_question instead of workers table.
"""

import sqlite3

import pytest


@pytest.fixture
def task_in_progress(db_path):
    """Create epic and task in in_progress status for blocked state tests."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.execute(
            """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                42,
                "test-epic",
                "Test task",
                "Test description",
                "in_progress",
                "2025-01-01T00:00:00Z",
            ),
        )
        conn.commit()
    return 42


@pytest.fixture
def task_blocked_user(db_path):
    """Create epic and task in blocked_user status for resume tests."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.execute(
            """INSERT INTO tasks (id, epic_name, title, description, status, blocked_question, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                42,
                "test-epic",
                "Test task",
                "Test desc",
                "blocked_user",
                "Why is X not working?",
                "2025-01-01T00:00:00Z",
            ),
        )
        conn.commit()
    return 42


class TestBlockedCommandSetsTaskStatus:
    """Test that pm blocked transitions task to blocked_user status."""

    def test_blocked_command_transitions_task_to_blocked_user(
        self, db_path, task_in_progress, monkeypatch
    ):
        """pm blocked "question" transitions task to blocked_user status."""
        monkeypatch.setenv("TASK_ID", str(task_in_progress))

        from formaltask.cli.commands import blocked

        class Args:
            question = "Why is X not working?"
            db_path = None

        args = Args()
        args.db_path = db_path

        exit_code = blocked.execute(args)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_in_progress,))
            row = cursor.fetchone()

        assert row is not None, "Task should exist"
        assert row[0] == "blocked_user", f"Expected 'blocked_user', got '{row[0]}'"
        assert exit_code == 0

    def test_blocked_command_sets_blocked_question(self, db_path, task_in_progress, monkeypatch):
        """pm blocked "question" sets tasks.blocked_question."""
        monkeypatch.setenv("TASK_ID", str(task_in_progress))

        from formaltask.cli.commands import blocked

        class Args:
            question = "Why is X not working?"
            db_path = None

        args = Args()
        args.db_path = db_path

        blocked.execute(args)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT blocked_question FROM tasks WHERE id = ?", (task_in_progress,))
            row = cursor.fetchone()

        assert row is not None, "Task should exist"
        assert row[0] == "Why is X not working?", f"Expected question, got '{row[0]}'"


class TestGetBlockedWorkersQueriesTasks:
    """Test that get_blocked_workers() returns tasks where status='blocked_user'."""

    def test_get_blocked_workers_returns_tasks_with_blocked_user_status(
        self, db_path, task_blocked_user, tmp_path
    ):
        """get_blocked_workers() returns tasks where status='blocked_user'."""
        from formaltask.workers.inbox import get_blocked_workers

        workers = get_blocked_workers(db_path, projects_dir=str(tmp_path))

        assert len(workers) == 1, f"Expected 1 blocked worker, got {len(workers)}"
        assert workers[0]["task_id"] == task_blocked_user
        assert workers[0]["pending_question"] == "Why is X not working?"


class TestResumeClearsBlockedState:
    """Test that pm resume clears blocked state on tasks table."""

    def test_resume_clears_blocked_question(self, db_path, task_blocked_user, monkeypatch):
        """pm resume clears tasks.blocked_question."""
        monkeypatch.setattr("formaltask.workers.resume.get_db_path", lambda: db_path)

        from formaltask.workers.resume import _clear_blocked_state

        _clear_blocked_state(task_blocked_user)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT blocked_question FROM tasks WHERE id = ?", (task_blocked_user,))
            row = cursor.fetchone()

        assert row is not None, "Task should exist"
        assert row[0] is None, f"Expected NULL, got '{row[0]}'"

    def test_resume_transitions_task_to_in_progress(self, db_path, task_blocked_user, monkeypatch):
        """pm resume transitions task back to in_progress."""
        monkeypatch.setattr("formaltask.workers.resume.get_db_path", lambda: db_path)

        from formaltask.workers.resume import _clear_blocked_state

        _clear_blocked_state(task_blocked_user)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_blocked_user,))
            row = cursor.fetchone()

        assert row is not None, "Task should exist"
        assert row[0] == "in_progress", f"Expected 'in_progress', got '{row[0]}'"
