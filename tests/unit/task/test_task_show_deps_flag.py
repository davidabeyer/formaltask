"""Tests for --deps flag in task-show command (Task #2651).

TDD: Write tests first, then implement.
Merges task-deps functionality into task-show with --deps flag.
"""

import json
import sqlite3


def test_task_show_deps_flag_shows_dependency_tree(db_path):
    """Test that --deps flag shows task dependencies."""
    from formaltask.cli.commands.task_show import task_show

    # Create epic and tasks with dependency
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at, depends_on, is_parallel) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("test-epic", "Parent task", "Parent", "completed", 1, "2025-01-01T00:00:00Z", "[]", 0),
        )
        parent_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at, depends_on, is_parallel) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "test-epic",
                "Child task",
                "Child",
                "open",
                2,
                "2025-01-01T00:00:00Z",
                json.dumps([parent_id]),
                1,
            ),
        )
        child_id = cursor.lastrowid
        conn.commit()

    # When: Calling task_show with show_deps=True
    result = task_show(child_id, db_path, show_deps=True)

    # Then: Should include dependency info
    assert "dependencies" in result
    assert "dependents" in result
    assert "is_parallel" in result
    assert len(result["dependencies"]) == 1
    assert result["dependencies"][0]["id"] == parent_id


def test_task_show_deps_flag_shows_dependents(db_path):
    """Test that --deps shows tasks that depend on this task."""
    from formaltask.cli.commands.task_show import task_show

    # Create epic and tasks
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at, depends_on) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test-epic", "Parent task", "Parent", "open", 1, "2025-01-01T00:00:00Z", "[]"),
        )
        parent_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at, depends_on) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "test-epic",
                "Child task",
                "Child",
                "open",
                2,
                "2025-01-01T00:00:00Z",
                json.dumps([parent_id]),
            ),
        )
        child_id = cursor.lastrowid
        conn.commit()

    # When: Calling task_show on parent with show_deps=True
    result = task_show(parent_id, db_path, show_deps=True)

    # Then: Should show child as dependent
    assert "dependents" in result
    assert len(result["dependents"]) == 1
    assert result["dependents"][0]["id"] == child_id


def test_task_show_without_deps_flag_basic_info(db_path):
    """Test that task_show without --deps still works (backward compat)."""
    from formaltask.cli.commands.task_show import task_show

    # Create epic and task
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at, depends_on) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test-epic", "Test task", "Desc", "open", 1, "2025-01-01T00:00:00Z", "[]"),
        )
        task_id = cursor.lastrowid
        conn.commit()

    # When: Calling task_show without show_deps
    result = task_show(task_id, db_path)

    # Then: Should return basic info
    assert result["task_id"] == task_id
    assert result["title"] == "Test task"
    assert result["status"] == "open"
    # Should NOT include deps info by default
    assert "dependencies" not in result


def test_task_show_not_found(db_path):
    """Test that task_show returns empty dict for nonexistent task."""
    from formaltask.cli.commands.task_show import task_show

    assert task_show(9999, db_path) == {}


def test_cli_task_show_deps_flag(db_path):
    """Test CLI with --deps flag outputs dependency info."""
    import subprocess
    import sys

    # Setup
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at, depends_on, is_parallel) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("test-epic", "Test task", "Desc", "open", 1, "2025-01-01T00:00:00Z", "[]", 1),
        )
        task_id = cursor.lastrowid
        conn.commit()

    # When: Running CLI with --deps flag
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "task", "show",
            str(task_id),
            "--deps",
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
    )

    # Then: Should succeed and include both dependency sections
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "Depends on:" in result.stdout
    assert "Dependents:" in result.stdout


def test_cli_task_show_help_contains_deps_flag():
    """Acceptance criteria: ft task-show --help contains '--deps'."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "formaltask.cli.pm", "task", "show", "--help"],
        capture_output=True,
        text=True,
    )

    assert "--deps" in result.stdout, f"--deps not found in help output: {result.stdout}"
