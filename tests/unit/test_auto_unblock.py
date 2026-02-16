"""Tests for auto-unblock reporter when blocker task completes.

When a blocker task (created via `ft work report`) completes, the reporter
task should auto-resume if it's in blocked_user status.
"""

import json
import sqlite3


def _create_epic(db_path):
    """Create a test epic."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()


def _create_task(db_path, task_id, *, status="in_progress", metadata=None):
    """Create a task with given id, status, and metadata."""
    metadata_json = json.dumps(metadata) if metadata else None
    blocked_question = "Waiting for fix" if status == "blocked_user" else None
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO tasks (id, epic_name, title, description, status,
               blocked_question, created_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task_id,
                "test-epic",
                f"Task {task_id}",
                f"Task {task_id} desc",
                status,
                blocked_question,
                "2025-01-01T00:00:00Z",
                metadata_json,
            ),
        )
        conn.commit()


class TestAutoUnblockReporter:
    """Tests for _auto_unblock_reporter()."""

    def test_blocker_completes_unblocks_reporter(self, db_path, monkeypatch, capsys):
        """Blocker task completes → source task blocked_user → auto-resumed."""
        from formaltask.cli.commands.task_complete import _auto_unblock_reporter

        _create_epic(db_path)
        _create_task(db_path, 100, status="blocked_user")
        _create_task(
            db_path,
            200,
            status="completed",
            metadata={"task_type": "blocker", "source_task_id": 100},
        )

        resume_calls = []
        monkeypatch.setattr(
            "formaltask.cli.commands.task_complete.resume_worker_in_tmux",
            lambda task_id, response: resume_calls.append((task_id, response)) or f"task-{task_id}",
        )

        _auto_unblock_reporter(200, db_path)

        # resume_worker_in_tmux was called with correct args
        assert len(resume_calls) == 1
        assert resume_calls[0][0] == 100
        assert "Blocker task #200 completed" in resume_calls[0][1]

        # Confirmation printed
        captured = capsys.readouterr()
        assert "Auto-resumed task #100" in captured.out

    def test_source_not_blocked_is_noop(self, db_path):
        """Blocker completes → source task NOT blocked_user → no-op."""
        from formaltask.cli.commands.task_complete import _auto_unblock_reporter

        _create_epic(db_path)
        # Reporter is in_progress (not blocked)
        _create_task(db_path, 100, status="in_progress")
        _create_task(
            db_path,
            200,
            status="completed",
            metadata={"task_type": "blocker", "source_task_id": 100},
        )

        # Should not raise, just return
        _auto_unblock_reporter(200, db_path)

        # Status unchanged
        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT status FROM tasks WHERE id = 100").fetchone()
        assert row[0] == "in_progress"

    def test_non_blocker_task_is_noop(self, db_path):
        """Non-blocker task completes → no metadata → no-op."""
        from formaltask.cli.commands.task_complete import _auto_unblock_reporter

        _create_epic(db_path)
        _create_task(db_path, 100, status="in_progress")

        # Should not raise
        _auto_unblock_reporter(100, db_path)

    def test_blocker_without_source_task_id_is_noop(self, db_path):
        """Blocker task with no source_task_id → no-op."""
        from formaltask.cli.commands.task_complete import _auto_unblock_reporter

        _create_epic(db_path)
        _create_task(
            db_path,
            200,
            status="completed",
            metadata={"task_type": "blocker"},
        )

        # Should not raise
        _auto_unblock_reporter(200, db_path)

    def test_resume_failure_falls_back_to_clear_state(self, db_path, monkeypatch, capsys):
        """Resume fails → falls back to _clear_blocked_state + prints hint."""
        from formaltask.cli.commands.task_complete import _auto_unblock_reporter

        _create_epic(db_path)
        _create_task(db_path, 100, status="blocked_user")
        _create_task(
            db_path,
            200,
            status="completed",
            metadata={"task_type": "blocker", "source_task_id": 100},
        )

        # resume_worker_in_tmux raises
        def mock_resume(task_id, response):
            raise RuntimeError("tmux not available")

        monkeypatch.setattr(
            "formaltask.cli.commands.task_complete.resume_worker_in_tmux",
            mock_resume,
        )

        _auto_unblock_reporter(200, db_path)

        # State should still be cleared via fallback
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT status, blocked_question FROM tasks WHERE id = 100"
            ).fetchone()
        assert row[0] == "in_progress"
        assert row[1] is None

        # Should print respawn hint
        captured = capsys.readouterr()
        assert "respawn" in captured.out.lower() or "ft work spawn" in captured.out
