"""Tests for pm-task-add CLI command."""

import json
import sqlite3
import subprocess
import sys


def test_task_add_cli_multiple_criteria_flags(db_path):
    """Bug #871: Multiple --criteria flags should accumulate all criteria.

    The CLI argparse uses action='append' to collect multiple --criteria flags.
    This test verifies all criteria are saved, not just the last one.
    """
    # Setup: Create epic
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    # When: Running CLI with multiple --criteria flags
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "task", "add",
            "test-epic",
            "Multi-criteria task",
            "Testing multiple criteria",
            "--criteria",
            "First criterion",
            "--criteria",
            "Second criterion",
            "--criteria",
            "Third criterion",
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
    )

    # Then: Command should succeed
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "Added task #" in result.stdout

    # And: All criteria should be saved
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tasks WHERE title = 'Multi-criteria task'")
        task = cursor.fetchone()
        assert task is not None, "Task should exist"
        task_id = task[0]

        cursor.execute(
            "SELECT text FROM acceptance_criteria WHERE task_id = ? ORDER BY id", (task_id,)
        )
        criteria = [row[0] for row in cursor.fetchall()]

    assert len(criteria) == 3, f"Expected 3 criteria, got {len(criteria)}: {criteria}"
    assert criteria[0] == "First criterion"
    assert criteria[1] == "Second criterion"
    assert criteria[2] == "Third criterion"


def test_task_add_cli_depends_on_flag(db_path):
    """Issue #975: CLI --depends-on flag should work via command line."""
    # Setup: Create epic and parent task
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        # Create parent task directly in DB
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("test-epic", "Parent task", "Parent description", "open", 1, "2025-01-01T00:00:00Z"),
        )
        parent_task_id = cursor.lastrowid
        conn.commit()

    # When: Running CLI with --depends-on flag
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "task", "add",
            "test-epic",
            "Child task",
            "Child description",
            "--criteria",
            "Child criterion",
            "--depends-on",
            str(parent_task_id),
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
    )

    # Then: Command should succeed
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "Added task #" in result.stdout

    # And: depends_on should be set correctly
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, depends_on FROM tasks WHERE title = 'Child task'")
        task = cursor.fetchone()

    assert task is not None, "Child task should exist"
    depends_on = json.loads(task[1])
    assert depends_on == [parent_task_id], f"Expected [{parent_task_id}], got {depends_on}"


def test_task_add_cli_multiple_depends_on_flags(db_path):
    """Issue #975: Multiple --depends-on flags should accumulate all dependencies."""
    # Setup: Create epic and two parent tasks
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("test-epic", "Parent 1", "First parent", "open", 1, "2025-01-01T00:00:00Z"),
        )
        parent1_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("test-epic", "Parent 2", "Second parent", "open", 2, "2025-01-01T00:00:00Z"),
        )
        parent2_id = cursor.lastrowid
        conn.commit()

    # When: Running CLI with multiple --depends-on flags
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "task", "add",
            "test-epic",
            "Child task",
            "Depends on both parents",
            "--criteria",
            "Child criterion",
            "--depends-on",
            str(parent1_id),
            "--depends-on",
            str(parent2_id),
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
    )

    # Then: Command should succeed
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    # And: depends_on should contain both parent IDs
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT depends_on FROM tasks WHERE title = 'Child task'")
        task = cursor.fetchone()

    depends_on = json.loads(task[0])
    assert set(depends_on) == {parent1_id, parent2_id}, (
        f"Expected {{{parent1_id}, {parent2_id}}}, got {depends_on}"
    )
