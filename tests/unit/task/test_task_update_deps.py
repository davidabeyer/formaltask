"""Tests for task-update --depends-on and --clear-deps flags (Task #2800)."""

import json
import sqlite3
import subprocess
import sys


def test_task_update_depends_on_sets_single_dependency(db_path):
    """ft task-update 123 --depends-on 456 sets task 123 to depend on 456."""
    # Setup: Create epic and two tasks
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("test-epic", "Parent task", "Parent", "open", 1, "2025-01-01T00:00:00Z"),
        )
        parent_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("test-epic", "Child task", "Child", "open", 2, "2025-01-01T00:00:00Z"),
        )
        child_id = cursor.lastrowid
        conn.commit()

    # When: Running task-update with --depends-on
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "task", "update",
            str(child_id),
            "--depends-on",
            str(parent_id),
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
    )

    # Then: Command should succeed
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "dependencies" in result.stdout.lower() or "updated" in result.stdout.lower()

    # And: depends_on should be set correctly
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT depends_on FROM tasks WHERE id = ?", (child_id,))
        row = cursor.fetchone()

    depends_on = json.loads(row[0])
    assert depends_on == [parent_id], f"Expected [{parent_id}], got {depends_on}"


def test_task_update_depends_on_sets_multiple_dependencies(db_path):
    """ft task-update 123 --depends-on 456 --depends-on 789 sets multiple deps."""
    # Setup: Create epic and three tasks
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("test-epic", "Parent 1", "First parent", "open", 1, "2025-01-01T00:00:00Z"),
        )
        parent1_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("test-epic", "Parent 2", "Second parent", "open", 2, "2025-01-01T00:00:00Z"),
        )
        parent2_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("test-epic", "Child task", "Child", "open", 3, "2025-01-01T00:00:00Z"),
        )
        child_id = cursor.lastrowid
        conn.commit()

    # When: Running task-update with multiple --depends-on flags
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "task", "update",
            str(child_id),
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
        cursor.execute("SELECT depends_on FROM tasks WHERE id = ?", (child_id,))
        row = cursor.fetchone()

    depends_on = json.loads(row[0])
    assert set(depends_on) == {parent1_id, parent2_id}, (
        f"Expected {{{parent1_id}, {parent2_id}}}, got {depends_on}"
    )


def test_task_update_clear_deps_removes_all_dependencies(db_path):
    """ft task-update 123 --clear-deps removes all dependencies."""
    # Setup: Create epic with task that has dependencies
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("test-epic", "Parent task", "Parent", "open", 1, "2025-01-01T00:00:00Z"),
        )
        parent_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at, depends_on) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
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

    # Verify initial state has dependency
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT depends_on FROM tasks WHERE id = ?", (child_id,))
        row = cursor.fetchone()
    assert json.loads(row[0]) == [parent_id], "Initial state should have dependency"

    # When: Running task-update with --clear-deps
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "task", "update",
            str(child_id),
            "--clear-deps",
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
    )

    # Then: Command should succeed
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "cleared" in result.stdout.lower() or "dependencies" in result.stdout.lower()

    # And: depends_on should be empty
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT depends_on FROM tasks WHERE id = ?", (child_id,))
        row = cursor.fetchone()

    depends_on = json.loads(row[0])
    assert depends_on == [], f"Expected [], got {depends_on}"


def test_task_update_depends_on_and_clear_deps_mutually_exclusive(db_path):
    """ft task-update 123 --depends-on 456 --clear-deps errors."""
    # Setup: Create epic and two tasks
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("test-epic", "Parent task", "Parent", "open", 1, "2025-01-01T00:00:00Z"),
        )
        parent_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("test-epic", "Child task", "Child", "open", 2, "2025-01-01T00:00:00Z"),
        )
        child_id = cursor.lastrowid
        conn.commit()

    # When: Running task-update with both --depends-on and --clear-deps
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "task", "update",
            str(child_id),
            "--depends-on",
            str(parent_id),
            "--clear-deps",
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
    )

    # Then: Command should fail
    assert result.returncode != 0, "Should fail when --depends-on and --clear-deps are both used"
    # Error message should mention the conflict
    assert "mutually exclusive" in result.stderr.lower() or "cannot" in result.stderr.lower()


def test_task_update_depends_on_detects_circular_dependency(db_path):
    """Circular dependency detection works via update_task_dependencies."""
    # Setup: Create epic with task A depending on task B
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("test-epic", "Task A", "A", "open", 1, "2025-01-01T00:00:00Z"),
        )
        task_a_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO tasks (epic_name, title, description, status, position, created_at, depends_on) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "test-epic",
                "Task B",
                "B",
                "open",
                2,
                "2025-01-01T00:00:00Z",
                json.dumps([task_a_id]),
            ),
        )
        task_b_id = cursor.lastrowid
        conn.commit()

    # When: Trying to make Task A depend on Task B (would create A -> B -> A cycle)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "task", "update",
            str(task_a_id),
            "--depends-on",
            str(task_b_id),
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
    )

    # Then: Command should fail due to circular dependency
    assert result.returncode != 0, (
        f"Should fail on circular dep. stdout: {result.stdout}, stderr: {result.stderr}"
    )
    assert "circular" in result.stderr.lower(), (
        f"Error should mention circular. stderr: {result.stderr}"
    )
