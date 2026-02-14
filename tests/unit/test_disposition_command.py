"""Tests for pm disposition command (renamed from wontfix).

Task #2261: CLI command renamed from wontfix to disposition.
Task #2262: Add --needshuman flag support.
Task #2598: Add 'fixed' as first-class disposition.
"""

import argparse
import sqlite3

import pytest

from tests.conftest import PROJECT_ROOT


@pytest.fixture
def db_with_task(tmp_path):
    """Create a temp database with task and finding_dispositions table."""
    db_file = tmp_path / "test.db"
    schema_file = PROJECT_ROOT / "formaltask" / "data" / "schema.sql"

    with sqlite3.connect(db_file) as conn:
        conn.executescript(schema_file.read_text())

        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)

        python_migration_names = [
            "024_fix_workers_pid_nullable",
            "025_add_worker_state_columns",
            "026_consolidate_reviews",
            "032_drop_pending_decisions",
            "add_blocked_question_to_tasks",
            "add_blocked_summary",
            "add_completion_evidence",
            "add_epic_feature_branch",
            "add_pending_decisions",
            "add_pending_question",
            "add_plan_file_path",
            "add_reminder_count",
            "add_review_sha_and_round",
            "add_review_type",
            "add_reviewed_at",
            "add_round_to_task_reviews",
            "add_task_artifacts",
            "backfill_severity",
            "consolidate_reviews",
            "drop_pending_decisions",
            "drop_unused_worker_columns",
            "drop_worker_blocking_columns",
            "drop_worker_columns",
            "fix_epic_status_completed_count",
            "migrate_planning_json_to_db",
            "migrate_pr_merged_column",
            "migrate_remove_pr_columns",
            "migrate_v5_to_v6",
            "migrate_worker_columns",
            "migrate_worker_state_columns",
            "migrate_workers_pid_nullable",
            "rename_migration_028_to_029",
            "task_completion_state",
        ]
        for migration_name in python_migration_names:
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (name, applied_at) VALUES (?, datetime('now'))",
                (migration_name,),
            )

        conn.execute(
            "INSERT INTO epics (name, description, created_at) "
            "VALUES ('test-epic', 'Test', '2025-01-01')"
        )
        conn.execute(
            "INSERT INTO tasks (id, epic_name, title, description, created_at) "
            "VALUES (1, 'test-epic', 'Test Task', 'Test description', '2025-01-01')"
        )
        conn.execute(
            "INSERT INTO work_sessions (worktree_path, current_task_id) VALUES (?, 1)",
            (str(tmp_path),),
        )
        conn.commit()

    return db_file


def test_parser_supports_needshuman_fixed_mutually_exclusive():
    """Parser supports --needshuman, --fixed flags and enforces mutual exclusion."""
    from formaltask.cli.commands import disposition

    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers()
    sub = subparser.add_parser("disposition")
    disposition.setup_parser(sub)

    args = parser.parse_args(["disposition", "foo.py", "10", "--needshuman"])
    assert args.needshuman is True

    args = parser.parse_args(["disposition", "foo.py", "10", "--fixed"])
    assert args.fixed is True

    with pytest.raises(SystemExit):
        parser.parse_args(["disposition", "foo.py", "10", "--fixed", "--needshuman"])


def test_needshuman_blocks_task_with_context(db_with_task, tmp_path, monkeypatch):
    """--needshuman sets disposition='needshuman', task status to blocked_user, and blocked_question."""
    import os

    from formaltask.cli.commands import disposition

    monkeypatch.setattr(os, "getcwd", lambda: str(tmp_path))

    with sqlite3.connect(db_with_task) as conn:
        conn.execute("UPDATE tasks SET status = 'in_progress' WHERE id = 1")
        conn.commit()

    args = argparse.Namespace(
        file="auth/login.py",
        line=42,
        reason="Security tradeoff needs architect review",
        task=1,
        list=False,
        clear=False,
        needshuman=True,
        fixed=False,
        db_path=str(db_with_task),
    )

    result = disposition.execute(args)
    assert result == 0

    with sqlite3.connect(db_with_task) as conn:
        cursor = conn.execute(
            "SELECT disposition FROM finding_dispositions WHERE task_id = 1 AND file = 'auth/login.py'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "needshuman"

        cursor = conn.execute("SELECT status, blocked_question FROM tasks WHERE id = 1")
        row = cursor.fetchone()
        assert row[0] == "blocked_user"
        assert "auth/login.py:42" in row[1]
        assert "Security tradeoff needs architect review" in row[1]


def test_needshuman_returns_invalid_state_for_completed_task(db_with_task, tmp_path, monkeypatch):
    """--needshuman on completed task returns INVALID_STATE exit code."""
    import os

    from formaltask.cli.commands import disposition
    from formaltask.cli.exit_codes import ExitCode

    monkeypatch.setattr(os, "getcwd", lambda: str(tmp_path))

    with sqlite3.connect(db_with_task) as conn:
        conn.execute("UPDATE tasks SET status = 'completed' WHERE id = 1")
        conn.commit()

    args = argparse.Namespace(
        file="foo.py",
        line=10,
        reason="Too late for blocking",
        task=1,
        list=False,
        clear=False,
        needshuman=True,
        fixed=False,
        db_path=str(db_with_task),
    )

    result = disposition.execute(args)
    assert result == ExitCode.INVALID_STATE


def test_fixed_records_disposition_without_blocking(db_with_task, tmp_path, monkeypatch):
    """--fixed sets disposition='fixed' and does NOT block the task."""
    import os

    from formaltask.cli.commands import disposition

    monkeypatch.setattr(os, "getcwd", lambda: str(tmp_path))

    with sqlite3.connect(db_with_task) as conn:
        conn.execute("UPDATE tasks SET status = 'in_progress' WHERE id = 1")
        conn.commit()

    args = argparse.Namespace(
        file="bug.py",
        line=42,
        reason="Fixed the null pointer bug",
        task=1,
        list=False,
        clear=False,
        needshuman=False,
        fixed=True,
        db_path=str(db_with_task),
    )

    result = disposition.execute(args)
    assert result == 0

    with sqlite3.connect(db_with_task) as conn:
        cursor = conn.execute(
            "SELECT disposition FROM finding_dispositions WHERE task_id = 1 AND file = 'bug.py'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "fixed"

        cursor = conn.execute("SELECT status FROM tasks WHERE id = 1")
        row = cursor.fetchone()
        assert row[0] == "in_progress"


def test_default_disposition_is_wontfix(db_with_task, tmp_path, monkeypatch):
    """Without --fixed or --needshuman, disposition is 'wontfix'."""
    import os

    from formaltask.cli.commands import disposition

    monkeypatch.setattr(os, "getcwd", lambda: str(tmp_path))

    args = argparse.Namespace(
        file="legacy.py",
        line=100,
        reason="Pre-existing code style issue",
        task=1,
        list=False,
        clear=False,
        needshuman=False,
        fixed=False,
        db_path=str(db_with_task),
    )

    result = disposition.execute(args)
    assert result == 0

    with sqlite3.connect(db_with_task) as conn:
        cursor = conn.execute(
            "SELECT disposition FROM finding_dispositions WHERE task_id = 1 AND file = 'legacy.py'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "wontfix"
