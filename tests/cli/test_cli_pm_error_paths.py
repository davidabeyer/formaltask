"""Tests for CLI error paths (formaltask.cli.pm).

Task #622: Fix P2 Test coverage gaps - weak assertions and missing verification
"""

import os
import sqlite3
import subprocess
import sys

import pytest


def test_cli_invalid_subcommand_shows_error():
    """Test that invalid subcommand shows error message."""
    # When: Running with invalid subcommand
    result = subprocess.run(
        [sys.executable, "-m", "formaltask.cli.pm", "invalid-command"],
        capture_output=True,
        text=True,
    )

    # Task #693: Verify specific exit code and stderr content
    # Then: Should fail with specific exit code (1 = general error, 2 = usage error)
    assert result.returncode in (
        1,
        2,
    ), f"Invalid subcommand should return exit code 1 or 2, got {result.returncode}"
    # Error message should be in stderr (not stdout) for proper CLI behavior
    error_output = result.stderr.lower()
    assert any(x in error_output for x in ["invalid", "unknown", "unrecognized", "error"]), (
        f"Should show error in stderr about invalid command. stderr: {result.stderr!r}"
    )
    # stdout should NOT contain error messages (proper CLI convention)
    assert "error" not in result.stdout.lower() or result.stderr, (
        f"Error messages should go to stderr, not stdout. stdout: {result.stdout!r}"
    )


# Task #2646: test_cli_task_start_missing_task_id removed - task_start.py deleted
# Task #2646: test_cli_task_start_nonexistent_task_id removed - task_start.py deleted
# Task #2646: test_cli_task_start_sets_all_expected_fields removed - task_start.py deleted


def test_cli_task_add_creates_all_expected_records(db_with_epic):
    """Test that task-add creates task and acceptance_criteria records."""
    db_file = db_with_epic

    # When: Running task-add with multiple criteria
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "task",
            "add",
            "test-epic",
            "New Task Title",
            "Detailed task description",
            "--criteria",
            "First criterion",
            "--criteria",
            "Second criterion",
            "--criteria",
            "Third criterion",
            "--db-path",
            str(db_file),
        ],
        capture_output=True,
        text=True,
    )

    # Then: Should succeed
    assert result.returncode == 0, f"Command should succeed. stderr: {result.stderr}"

    # And: Verify task record with all fields
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, epic_name, title, description, status, position FROM tasks")
        task = cursor.fetchone()

    assert task is not None, "Task should exist"
    task_id, epic_name, title, description, status, position = task

    # Stronger assertions
    assert epic_name == "test-epic", f"Epic name should match, got '{epic_name}'"
    assert title == "New Task Title", f"Title should match, got '{title}'"
    assert description == "Detailed task description", (
        f"Description should match, got '{description}'"
    )
    assert status == "open", f"Status should be 'open', got '{status}'"
    assert position == 1, f"Position should be 1, got {position}"

    # And: Verify ALL acceptance criteria records
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT text, checked FROM acceptance_criteria WHERE task_id = ? ORDER BY id",
            (task_id,),
        )
        criteria = cursor.fetchall()

    assert len(criteria) == 3, f"Should have 3 criteria, got {len(criteria)}"
    assert criteria[0][0] == "First criterion", f"First criterion text mismatch: {criteria[0][0]}"
    assert criteria[1][0] == "Second criterion", f"Second criterion text mismatch: {criteria[1][0]}"
    assert criteria[2][0] == "Third criterion", f"Third criterion text mismatch: {criteria[2][0]}"

    # All should be unchecked initially
    for text, checked in criteria:
        assert checked == 0, f"Criterion '{text}' should be unchecked, got {checked}"


def test_cli_task_complete_sets_all_expected_fields(db_with_epic):
    """Test that task-complete sets status, completed_at correctly."""
    db_file = db_with_epic

    # Given: Database with started task that has commit evidence
    with sqlite3.connect(db_file) as conn:
        # Note: review_status column removed in Task #2013
        conn.execute(
            "INSERT INTO tasks (id, epic_name, title, description, status, created_at, started_at) "
            "VALUES (1, 'test-epic', 'Complete Me', 'Description', 'in_progress', '2025-01-01T00:00:00Z', '2025-01-01T01:00:00Z')"
        )
        conn.execute(
            "INSERT INTO commits (task_id, commit_hash, commit_message) "
            "VALUES (1, 'abc123def', 'Test commit message')"  # pragma: allowlist secret
        )
        # Add clean review to pass gate enforcement (Task #2234)
        # Default required review is 'code-quality' per rules_config.py
        conn.execute(
            "INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at) "
            "VALUES (1, 'code-quality', 'clean', '[]', '2025-01-01T02:00:00Z')"
        )
        conn.commit()

    # When: Running task-complete
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

    # And: Verify ALL expected fields
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, status, started_at, completed_at FROM tasks WHERE id = 1")
        row = cursor.fetchone()

    assert row is not None, "Task should exist"
    task_id, status, started_at, completed_at = row

    # Stronger assertions
    assert task_id == 1, "Task ID should be 1"
    assert status == "completed", f"Status should be 'completed', got '{status}'"
    assert started_at is not None, "started_at should still be set"
    assert completed_at is not None, "completed_at should be set"
    assert "T" in completed_at, f"completed_at should be ISO format, got '{completed_at}'"
    # completed_at should be after started_at (lexicographic comparison works for ISO format)
    assert completed_at > started_at, (
        f"completed_at ({completed_at}) should be after started_at ({started_at})"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
