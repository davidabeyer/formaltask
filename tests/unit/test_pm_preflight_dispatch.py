"""Tests for preflight and dry-run flag dispatch in pm.py.

Task #1427: Fix preflight/dry-run flag dispatch.

These tests verify that --preflight and --dry-run flags are correctly
passed from the CLI dispatcher to command functions.
"""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from tests.fixtures.paths import SCHEMA_FILE


def _setup_test_db(tmp_path: Path) -> Path:
    """Create a test database with a pending task."""
    db_file = tmp_path / "test.db"

    with sqlite3.connect(db_file) as conn:
        with open(SCHEMA_FILE) as f:
            conn.executescript(f.read())

        # Create epic and task
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO tasks (id, epic_name, title, description, status, created_at) "
            "VALUES (1, 'test-epic', 'Test task', 'Desc', 'open', '2025-01-01T00:00:00Z')"
        )
        conn.execute(
            "INSERT INTO acceptance_criteria (task_id, text, checked) VALUES (1, 'Criterion', FALSE)"
        )
        conn.commit()

    return db_file


# Task #2646: task_start tests removed - task_start.py deleted (use spawn --no-worker)


def test_task_complete_preflight_does_not_modify_database(tmp_path):
    """Test that --preflight flag with task-complete doesn't modify the database."""
    db_file = _setup_test_db(tmp_path)

    # First start the task to make it in_progress
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "UPDATE tasks SET status = 'in_progress', started_at = '2025-01-01T01:00:00Z' "
            "WHERE id = 1"
        )
        # Add commit evidence
        conn.execute(
            "INSERT INTO commits (task_id, commit_hash, commit_message) "
            "VALUES (1, 'abc123', 'Test commit')"
        )
        conn.commit()

    # When: Running task-complete with --preflight flag
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "--json",
            "--preflight",
            "task",
            "complete",
            "1",
            "--db-path",
            str(db_file),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Should succeed. stderr: {result.stderr}"

    # Verify JSON response contains preflight structure
    response = json.loads(result.stdout)
    assert "preflight" in response.get("data", response), (
        f"Response should contain 'preflight' key, got: {result.stdout}"
    )

    # Then: Database should NOT be modified (preflight = validate only)
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, completed_at FROM tasks WHERE id = 1")
        row = cursor.fetchone()
        status, completed_at = row

    assert status == "in_progress", f"status should remain 'in_progress' (preflight), got: {status}"
    assert completed_at is None, f"completed_at should be None (preflight), got: {completed_at}"


def test_task_complete_dry_run_does_not_modify_database(tmp_path):
    """Test that --dry-run flag with task-complete doesn't modify the database."""
    db_file = _setup_test_db(tmp_path)

    # First start the task to make it in_progress
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "UPDATE tasks SET status = 'in_progress', started_at = '2025-01-01T01:00:00Z' "
            "WHERE id = 1"
        )
        # Add commit evidence
        conn.execute(
            "INSERT INTO commits (task_id, commit_hash, commit_message) "
            "VALUES (1, 'abc123', 'Test commit')"
        )
        conn.commit()

    # When: Running task-complete with --dry-run flag
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "--json",
            "--dry-run",
            "task",
            "complete",
            "1",
            "--db-path",
            str(db_file),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Should succeed. stderr: {result.stderr}"

    # Verify JSON response contains dry_run structure
    response = json.loads(result.stdout)
    assert "dry_run" in response.get("data", response), (
        f"Response should contain 'dry_run' key, got: {result.stdout}"
    )

    # Then: Database should NOT be modified (dry-run = preview only)
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, completed_at FROM tasks WHERE id = 1")
        row = cursor.fetchone()
        status, completed_at = row

    assert status == "in_progress", f"status should remain 'in_progress' (dry_run), got: {status}"
    assert completed_at is None, f"completed_at should be None (dry_run), got: {completed_at}"
