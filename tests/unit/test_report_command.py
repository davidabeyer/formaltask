"""Tests for ft work report command.

Task #2926: Verify ft work report creates blocker tasks with dedup.
"""

import json
import sqlite3
from argparse import Namespace

import pytest


@pytest.fixture
def report_context(db_path, repo, monkeypatch):
    """Create a worker context for report command tests.

    Sets up an epic with one in_progress task (the "worker" task),
    and sets TASK_ID env var.
    """
    repo.create_epic("test-epic", "Test epic")
    worker_task_id = repo.create_task("test-epic", "Worker task", "Doing work", ["criterion"])
    # Mark as in_progress (simulates a worker session)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE tasks SET status = 'in_progress' WHERE id = ?", (worker_task_id,))
        conn.commit()
    monkeypatch.setenv("TASK_ID", str(worker_task_id))
    return {"worker_task_id": worker_task_id, "db_path": db_path, "epic_name": "test-epic"}


class TestReportCreatesBlockerTask:
    """AC: ft work report creates task with task_type=blocker in metadata."""

    def test_report_creates_blocker_task(self, report_context):
        """ft work report creates a new task with task_type=blocker and required_reviews."""
        from formaltask.cli.commands.report import execute

        args = Namespace(
            description="Fix: test infrastructure issue",
            db_path=report_context["db_path"],
        )
        result = execute(args)
        assert result == 0

        # Verify blocker task created
        with sqlite3.connect(report_context["db_path"]) as conn:
            row = conn.execute(
                "SELECT id, title, metadata, epic_name, status FROM tasks WHERE title = ?",
                ("Fix: test infrastructure issue",),
            ).fetchone()

        assert row is not None, "Blocker task should be created"
        task_id, title, metadata_json, epic_name, status = row
        metadata = json.loads(metadata_json)

        assert metadata["task_type"] == "blocker"
        assert metadata["required_reviews"] == ["self-critique"]
        assert epic_name == report_context["epic_name"]
        assert status == "open"

    def test_report_no_task_context_returns_error(self, db_path, monkeypatch, capsys):
        """Running outside worker session returns NOT_FOUND."""
        from formaltask.cli.commands import report
        from formaltask.cli.exit_codes import ExitCode

        monkeypatch.setattr(report, "get_task_id_from_session", lambda: None)

        args = Namespace(description="Some issue", db_path=db_path)
        result = report.execute(args)

        assert result == ExitCode.NOT_FOUND
        captured = capsys.readouterr()
        assert "No task context" in captured.err


class TestReportDedup:
    """AC: Second ft work report for same epic returns existing (dedup works)."""

    def test_second_report_returns_existing(self, report_context, capsys):
        """Second ft work report for same epic deduplicates."""
        from formaltask.cli.commands.report import execute

        args1 = Namespace(
            description="Fix: test infrastructure issue",
            db_path=report_context["db_path"],
        )
        result1 = execute(args1)
        assert result1 == 0

        # Count blocker tasks
        with sqlite3.connect(report_context["db_path"]) as conn:
            count_before = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE json_extract(metadata, '$.task_type') = 'blocker'",
            ).fetchone()[0]

        args2 = Namespace(
            description="Another issue",
            db_path=report_context["db_path"],
        )
        result2 = execute(args2)
        assert result2 == 0

        # Same number of blocker tasks (dedup)
        with sqlite3.connect(report_context["db_path"]) as conn:
            count_after = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE json_extract(metadata, '$.task_type') = 'blocker'",
            ).fetchone()[0]

        assert count_after == count_before, "Should not create a second blocker task"

        # Verify output mentions existing task
        captured = capsys.readouterr()
        assert "existing" in captured.out.lower() or "already" in captured.out.lower()


class TestBlockerSpawnable:
    """AC: Blocker task is spawnable and picked up by ft work spawn."""

    def test_blocker_task_is_open_and_spawnable(self, report_context):
        """Blocker task created with status=open appears in spawnable list."""
        from formaltask.cli.commands.report import execute
        from formaltask.cli.commands.spawnable import spawnable

        args = Namespace(
            description="Fix: infrastructure issue",
            db_path=report_context["db_path"],
        )
        execute(args)

        # Get spawnable tasks
        tasks = spawnable(report_context["db_path"])
        blocker_tasks = [t for t in tasks if "infrastructure" in t.title.lower()]

        assert len(blocker_tasks) == 1, "Blocker task should appear in spawnable list"
        assert blocker_tasks[0].can_spawn, "Blocker task should have no blockers"
