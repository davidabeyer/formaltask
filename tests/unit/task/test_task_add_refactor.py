"""Tests for task-add command (Task #1377).

CLI behavior tests via subprocess - not testing internal functions.
"""

import json
import sqlite3
import subprocess
import sys

import pytest

from formaltask.cli.exit_codes import ExitCode
from formaltask.exceptions import EpicNotFoundError


def test_task_add_epic_not_found_json(db_path, repo):
    """task-add with non-existent epic returns CLIError with NOT_FOUND exit code."""
    # Given: No epic exists (empty database)

    # When: Running task-add for non-existent epic with --json
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "--json",
            "task", "add",
            "nonexistent-epic",
            "Test task",
            "Description",
            "--criteria",
            "Criterion",
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
    )

    # Then: Returns NOT_FOUND exit code (64)
    assert result.returncode == ExitCode.NOT_FOUND, (
        f"Expected exit code {ExitCode.NOT_FOUND}, got {result.returncode}. "
        f"stdout: {result.stdout}, stderr: {result.stderr}"
    )

    # And: JSON error response has correct structure
    response = json.loads(result.stdout)
    assert response["success"] is False
    assert "error" in response
    assert "not found" in response["error"]["message"].lower()


def test_task_add_json_success(db_path, repo):
    """task-add with --json returns valid JSON with new task_id."""
    # Given: An epic exists
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    # When: Running task-add with --json flag
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "--json",  # Global flag before subcommand
            "task", "add",
            "test-epic",
            "Test task",
            "Task description",
            "--criteria",
            "Test criterion",
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
    )

    # Then: Returns valid JSON with success=True and task_id
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    response = json.loads(result.stdout)
    assert response["success"] is True
    assert "data" in response
    assert "task_id" in response["data"]
    assert isinstance(response["data"]["task_id"], int)
    assert response["data"]["task_id"] > 0

    # P1: Verify task actually persisted to database with correct fields
    task_id = response["data"]["task_id"]
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title, description, epic_name FROM tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()
        assert task is not None, "Task not persisted to database"
        assert task[0] == "Test task", f"Task title incorrect: {task[0]}"
        assert task[1] == "Task description", f"Task description incorrect: {task[1]}"
        assert task[2] == "test-epic", f"Task epic_name incorrect: {task[2]}"


def test_get_epic_returns_full_data(db_path, repo):
    """get_epic() returns full epic data including description and timestamps."""
    from formaltask.epics import get_epic

    # Given: An epic exists with full data
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("full-data-epic", "Epic description", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    # When: Calling get_epic()
    epic = get_epic(db_path, "full-data-epic")

    # Then: Returns dict with full epic data
    assert epic is not None
    assert epic["name"] == "full-data-epic"
    assert epic["description"] == "Epic description"
    assert "created_at" in epic


def test_create_task_raises_epic_not_found_error(db_path, repo):
    """create_task() raises EpicNotFoundError for non-existent epic."""
    # Given: An empty database with no epics

    # When/Then: Attempting to create task raises EpicNotFoundError
    with pytest.raises(EpicNotFoundError) as exc_info:
        repo.create_task(
            epic_name="nonexistent-epic",
            title="Test task",
            description="Description",
            criteria=["Criterion"],
        )

    # And: Exception contains epic name
    assert exc_info.value.epic_name == "nonexistent-epic"
    assert "nonexistent-epic" in str(exc_info.value)
