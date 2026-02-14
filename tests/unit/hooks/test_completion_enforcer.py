"""Tests for completion_enforcer stop hook phase."""

import json
import tempfile
from pathlib import Path

import pytest

from formaltask.db.connection import DatabaseConnection


@pytest.fixture
def temp_db():
    """Create a temporary database with tasks table."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    with DatabaseConnection(db_path) as conn:
        conn.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                status TEXT NOT NULL
            )
        """)
        conn.commit()
    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def temp_transcript(tmp_path):
    """Create a temporary transcript file."""
    transcript = tmp_path / "transcript.jsonl"
    return str(transcript)


def write_transcript(path: str, entries: list[dict]):
    """Write entries to transcript file."""
    with open(path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


class TestCheckCompletionTerminalStatuses:
    """Terminal statuses should not block stop."""

    def test_returns_none_for_completed_status(self, temp_db):
        """Completed = terminal = no block."""
        from hooks.stop.phases.completion_enforcer import check_completion

        with DatabaseConnection(temp_db) as conn:
            conn.execute("INSERT INTO tasks (id, status) VALUES (1, 'completed')")
            conn.commit()

        ctx = {"task_id": 1, "db_path": temp_db}
        result = check_completion(ctx)

        assert result is None

    def test_returns_none_for_cancelled_status(self, temp_db):
        """Cancelled = terminal = no block."""
        from hooks.stop.phases.completion_enforcer import check_completion

        with DatabaseConnection(temp_db) as conn:
            conn.execute("INSERT INTO tasks (id, status) VALUES (1, 'cancelled')")
            conn.commit()

        ctx = {"task_id": 1, "db_path": temp_db}
        result = check_completion(ctx)

        assert result is None

    def test_returns_none_for_blocked_user_status(self, temp_db):
        """blocked_user = terminal = no block."""
        from hooks.stop.phases.completion_enforcer import check_completion

        with DatabaseConnection(temp_db) as conn:
            conn.execute("INSERT INTO tasks (id, status) VALUES (1, 'blocked_user')")
            conn.commit()

        ctx = {"task_id": 1, "db_path": temp_db}
        result = check_completion(ctx)

        assert result is None


class TestCheckCompletionNonTerminalStatuses:
    """Non-terminal statuses should block stop."""

    def test_returns_block_for_in_progress_status(self, temp_db):
        """Non-terminal = block with ft task-complete message."""
        from hooks.stop.phases.completion_enforcer import check_completion

        with DatabaseConnection(temp_db) as conn:
            conn.execute("INSERT INTO tasks (id, status) VALUES (42, 'in_progress')")
            conn.commit()

        ctx = {"task_id": 42, "db_path": temp_db}
        result = check_completion(ctx)

        assert result is not None
        assert result["decision"] == "block"
        assert "ft task complete 42" in result["reason"]


class TestCheckCompletionBypassConditions:
    """Conditions that bypass completion check."""

    def test_returns_none_when_last_tool_was_askuserquestion(self, temp_db, temp_transcript):
        """Waiting tool = no block (preserve behavior)."""
        from hooks.stop.phases.completion_enforcer import check_completion

        with DatabaseConnection(temp_db) as conn:
            conn.execute("INSERT INTO tasks (id, status) VALUES (1, 'in_progress')")
            conn.commit()

        write_transcript(temp_transcript, [{"type": "tool_use", "name": "AskUserQuestion"}])

        ctx = {"task_id": 1, "db_path": temp_db, "transcript_path": temp_transcript}
        result = check_completion(ctx)

        assert result is None

    def test_returns_none_when_stop_hook_active(self, temp_db):
        """Prevent infinite loop."""
        from hooks.stop.phases.completion_enforcer import check_completion

        with DatabaseConnection(temp_db) as conn:
            conn.execute("INSERT INTO tasks (id, status) VALUES (1, 'in_progress')")
            conn.commit()

        ctx = {"task_id": 1, "db_path": temp_db, "stop_hook_active": True}
        result = check_completion(ctx)

        assert result is None

    def test_returns_none_when_no_task_id(self, temp_db):
        """No task_id = no block."""
        from hooks.stop.phases.completion_enforcer import check_completion

        ctx = {"db_path": temp_db}
        result = check_completion(ctx)

        assert result is None

    def test_returns_none_when_no_db_path(self):
        """No db_path = no block."""
        from hooks.stop.phases.completion_enforcer import check_completion

        ctx = {"task_id": 1}
        result = check_completion(ctx)

        assert result is None

    def test_returns_none_when_task_not_found(self, temp_db):
        """Missing task = no block."""
        from hooks.stop.phases.completion_enforcer import check_completion

        ctx = {"task_id": 999, "db_path": temp_db}
        result = check_completion(ctx)

        assert result is None
