"""Tests for get_ready_tasks in epic_finalize command."""

import json

import pytest


@pytest.fixture
def db_with_tasks(tmp_path):
    """Create a test database with tasks, dependencies, and acceptance_criteria table."""
    import sqlite3

    db_path = tmp_path / "test.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                epic_name TEXT,
                title TEXT,
                description TEXT,
                depends_on TEXT,
                status TEXT DEFAULT 'open',
                metadata TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE acceptance_criteria (
                id INTEGER PRIMARY KEY,
                task_id INTEGER,
                text TEXT
            )
        """)

        # Insert test tasks:
        # Task 1: No dependencies, open -> READY
        # Task 2: Depends on Task 1 (open) -> NOT READY
        # Task 3: No dependencies, completed -> NOT READY (already done)
        # Task 4: Depends on Task 3 (completed) -> READY
        # Task 5: No dependencies, open -> READY
        cursor.execute(
            "INSERT INTO tasks (id, epic_name, title, depends_on, status) VALUES (?, ?, ?, ?, ?)",
            (1, "test-epic", "Task 1 - No deps", None, "open"),
        )
        cursor.execute(
            "INSERT INTO tasks (id, epic_name, title, depends_on, status) VALUES (?, ?, ?, ?, ?)",
            (2, "test-epic", "Task 2 - Blocked by 1", json.dumps([1]), "open"),
        )
        cursor.execute(
            "INSERT INTO tasks (id, epic_name, title, depends_on, status) VALUES (?, ?, ?, ?, ?)",
            (3, "test-epic", "Task 3 - Completed", None, "completed"),
        )
        cursor.execute(
            "INSERT INTO tasks (id, epic_name, title, depends_on, status) VALUES (?, ?, ?, ?, ?)",
            (4, "test-epic", "Task 4 - Dep completed", json.dumps([3]), "open"),
        )
        cursor.execute(
            "INSERT INTO tasks (id, epic_name, title, depends_on, status) VALUES (?, ?, ?, ?, ?)",
            (5, "test-epic", "Task 5 - No deps", None, "open"),
        )

        conn.commit()

    return str(db_path)


def test_get_ready_tasks_returns_tasks_without_blockers(db_with_tasks):
    """Tasks with no dependencies or completed dependencies are ready."""
    from formaltask.epics.validation import get_ready_tasks

    ready = get_ready_tasks(db_with_tasks, "test-epic")

    # Should return tasks 1, 4, and 5 (open with no blockers)
    ready_ids = [t["id"] for t in ready]
    assert 1 in ready_ids, "Task 1 (no deps) should be ready"
    assert 4 in ready_ids, "Task 4 (dep completed) should be ready"
    assert 5 in ready_ids, "Task 5 (no deps) should be ready"

    # Should NOT include task 2 (blocked) or task 3 (completed)
    assert 2 not in ready_ids, "Task 2 (blocked by open task) should not be ready"
    assert 3 not in ready_ids, "Task 3 (completed) should not be ready"


def test_epic_finalize_includes_ready_tasks_in_result(db_with_tasks):
    """epic_finalize result includes ready_tasks list."""
    from unittest.mock import patch

    from formaltask.epics.validation import epic_finalize

    # Mock validate_task_quality and detect_file_conflicts at source location
    with (
        patch("formaltask.epics.yaml_parser.validate_task_quality") as mock_validate,
        patch("formaltask.validators.file_conflict.detect_file_conflicts") as mock_detect,
    ):
        mock_validate.return_value = type("Result", (), {"errors": [], "warnings": []})()
        mock_detect.return_value = []
        result = epic_finalize("test-epic", db_with_tasks)

    assert "ready_tasks" in result
    ready_ids = [t["id"] for t in result["ready_tasks"]]
    assert 1 in ready_ids
    assert 4 in ready_ids
    assert 5 in ready_ids


def test_epic_finalize_detects_file_conflicts(db_with_tasks):
    """epic_finalize should detect and report file conflicts.

    Task #1991: parallel_safe removed (dead code). Dynamic spawnable handles
    conflicts at spawn time. epic_finalize provides analysis/validation only.
    """
    from unittest.mock import patch

    from formaltask.epics.validation import epic_finalize

    # Mock detect_file_conflicts to return conflicts between tasks 1 and 2
    with (
        patch("formaltask.epics.yaml_parser.validate_task_quality") as mock_validate,
        patch("formaltask.validators.file_conflict.detect_file_conflicts") as mock_detect,
    ):
        mock_validate.return_value = type("Result", (), {"errors": [], "warnings": []})()
        # File "shared.py" touched by tasks 1 and 2
        mock_detect.return_value = [("shared.py", [1, 2])]
        result = epic_finalize("test-epic", db_with_tasks)

    # File conflicts are detected and reported as file_hotspots/file_conflicts
    assert "file_hotspots" in result or "file_conflicts" in result
