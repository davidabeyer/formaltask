"""Tests for CLI entry point (formaltask.cli.pm).

Tests actual command behavior, not argparse internals.
"""

import os
import subprocess
import sys

from tests.fixtures.paths import PROJECT_ROOT, SCHEMA_FILE


def test_cli_error_has_message_attribute():
    """Test CLIError exception stores error message."""
    # Given: An error message
    from formaltask.cli.base import CLIError

    message = "Task not found"

    # When: Creating CLIError
    error = CLIError(message)

    # Then: Exception stores the message
    assert error.message == message
    assert str(error) == message


def test_cli_executes_task_add_command(tmp_path):
    """Test that CLI executes task-add command end-to-end."""
    # Given: Database with an epic
    import sqlite3

    db_file = tmp_path / "test.db"
    schema_file = SCHEMA_FILE

    with sqlite3.connect(db_file) as conn:
        with open(schema_file) as f:
            conn.executescript(f.read())

        # Pre-populate schema_migrations to prevent re-running migrations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)

        migrations_dir = PROJECT_ROOT / ".claude" / "migrations"
        if migrations_dir.exists():
            for migration_file in migrations_dir.glob("*.sql"):
                conn.execute(
                    "INSERT OR IGNORE INTO schema_migrations (name, applied_at) VALUES (?, datetime('now'))",
                    (migration_file.name,),
                )

        # Create epic
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    # When: Running task-add command
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "task",
            "add",
            "test-epic",
            "Test task",
            "Task description",
            "--criteria",
            "Criterion 1",
            "--criteria",
            "Criterion 2",
            "--db-path",
            str(db_file),
        ],
        capture_output=True,
        text=True,
    )

    # Then: Should succeed
    assert result.returncode == 0, f"Command should succeed. stderr: {result.stderr}"
    assert "Added task" in result.stdout, "Should show success message"

    # And: Task should exist in database
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, description FROM tasks")
        task = cursor.fetchone()
        assert task is not None
        assert task[1] == "Test task"
        assert task[2] == "Task description"

        # And: Criteria should exist
        cursor.execute("SELECT COUNT(*) FROM acceptance_criteria WHERE task_id = ?", (task[0],))
        count = cursor.fetchone()[0]

    assert count == 2, "Should have 2 acceptance criteria"


def test_cli_executes_task_complete_command(tmp_path):
    """Test that CLI executes task-complete command end-to-end."""
    # Given: Database with started task that has commits
    import sqlite3

    db_file = tmp_path / "test.db"
    schema_file = SCHEMA_FILE

    with sqlite3.connect(db_file) as conn:
        with open(schema_file) as f:
            conn.executescript(f.read())

        # Pre-populate schema_migrations to prevent re-running migrations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)

        migrations_dir = PROJECT_ROOT / ".claude" / "migrations"
        if migrations_dir.exists():
            for migration_file in migrations_dir.glob("*.sql"):
                conn.execute(
                    "INSERT OR IGNORE INTO schema_migrations (name, applied_at) VALUES (?, datetime('now'))",
                    (migration_file.name,),
                )
        conn.commit()

    # Create epic and task (review_status removed in Task #2013)
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO tasks (id, epic_name, title, description, status, created_at, started_at) "
            "VALUES (1, 'test-epic', 'Test', 'Desc', 'in_progress', '2025-01-01T00:00:00Z', '2025-01-01T01:00:00Z')"
        )
        conn.execute(
            "INSERT INTO acceptance_criteria (task_id, text, checked) VALUES (1, 'Criterion', FALSE)"
        )
        # Add commit evidence
        conn.execute(
            "INSERT INTO commits (task_id, commit_hash, commit_message) "
            "VALUES (1, 'abc123', 'Test commit')"
        )
        # Add clean review to pass gate enforcement (Task #2234)
        # Default required review is 'code-quality' per rules_config.py
        conn.execute(
            "INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at) "
            "VALUES (1, 'code-quality', 'clean', '[]', '2025-01-01T02:00:00Z')"
        )
        conn.commit()

    # When: Running task-complete command
    # Disable freshness check since test has no git repo context for reviewed_sha
    env = os.environ.copy()
    env["FORMALTASK_CHECK_FRESHNESS"] = "0"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "task",
            "complete",
            "1",
            "--db-path",
            str(db_file),
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    # Then: Should succeed
    assert result.returncode == 0, f"Command should succeed. stderr: {result.stderr}"
    assert "Completed task #1" in result.stdout, "Should show success message"

    # And: Task should be completed
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, completed_at FROM tasks WHERE id = 1")
        status, completed_at = cursor.fetchone()

    assert status == "completed"
    assert completed_at is not None


def test_cli_epic_sync_subcommand_removed():
    """Test that epic-sync subcommand has been removed.

    Task #1200: epic-sync was removed as part of GitHub sync removal.
    """
    # Given: CLI without epic-sync subcommand (removed in Task #1200)

    # When: Running python -m formaltask.cli.pm epic-sync test-epic
    result = subprocess.run(
        [sys.executable, "-m", "formaltask.cli.pm", "epic-sync", "test-epic"],
        capture_output=True,
        text=True,
    )

    # Then: Should fail with unknown command error (subcommand removed)
    assert result.returncode != 0, "epic-sync subcommand should not exist"
    assert "unknown command" in result.stderr.lower(), "Should show unknown command error"


def test_cli_executes_epic_review_command(tmp_path):
    """Test that CLI executes epic-review command end-to-end."""
    # Given: Database with epic that has completed tasks with no P0 issues
    import sqlite3

    from tests.conftest import make_valid_review_findings

    db_file = tmp_path / "test.db"
    schema_file = SCHEMA_FILE

    with sqlite3.connect(db_file) as conn:
        with open(schema_file) as f:
            conn.executescript(f.read())

        # Pre-populate schema_migrations to prevent re-running migrations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)

        migrations_dir = PROJECT_ROOT / ".claude" / "migrations"
        if migrations_dir.exists():
            for migration_file in migrations_dir.glob("*.sql"):
                conn.execute(
                    "INSERT OR IGNORE INTO schema_migrations (name, applied_at) VALUES (?, datetime('now'))",
                    (migration_file.name,),
                )
        conn.commit()

        # Create epic with 2 completed tasks
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO tasks (id, epic_name, title, description, status, created_at, started_at, completed_at) "
            "VALUES (1, 'test-epic', 'Task 1', 'Desc', 'completed', '2025-01-01T00:00:00Z', '2025-01-01T01:00:00Z', '2025-01-01T02:00:00Z')"
        )
        conn.execute(
            "INSERT INTO tasks (id, epic_name, title, description, status, created_at, started_at, completed_at) "
            "VALUES (2, 'test-epic', 'Task 2', 'Desc', 'completed', '2025-01-01T00:00:00Z', '2025-01-01T01:00:00Z', '2025-01-01T02:00:00Z')"
        )
        # Add task_reviews with P1 findings (not blocking)
        conn.execute(
            "INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at, round) VALUES (?, ?, ?, ?, ?, ?)",
            (
                1,
                "code-quality",
                "minor",
                make_valid_review_findings(["P1: Minor issue"], "Minor issue found"),
                "2025-01-01T03:00:00Z",
                1,
            ),
        )
        conn.execute(
            "INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at, round) VALUES (?, ?, ?, ?, ?, ?)",
            (
                2,
                "code-quality",
                "clean",
                make_valid_review_findings([], "Review approved"),
                "2025-01-01T03:00:00Z",
                1,
            ),
        )
        conn.commit()

    # When: Running epic-review command
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "epic",
            "review",
            "test-epic",
            "--db-path",
            str(db_file),
        ],
        capture_output=True,
        text=True,
    )

    # Then: Should succeed and show ready to merge
    assert result.returncode == 0, f"Command should succeed. stderr: {result.stderr}"
    assert "ready to merge" in result.stdout.lower(), "Should indicate ready to merge"
    assert "2/2" in result.stdout, "Should show completed task count"
