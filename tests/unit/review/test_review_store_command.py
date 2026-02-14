"""Tests for pm review-store command.

TDD tests for storing @@@REVIEW packets via CLI.
Workers call this after extracting review from Task tool output.
"""

import json
import sqlite3

# Note: db_path fixture is provided by hooks/tests/conftest.py


def test_review_store_valid_json_stores_successfully(db_path, repo):
    """Valid review JSON should INSERT into task_reviews table."""
    from formaltask.cli.commands.review_store import review_store

    # Create epic and task
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test Epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    task_id = repo.create_task("test-epic", "Test task", "Description", ["Criterion 1"])

    # Valid review packet
    review_json = json.dumps(
        {
            "task_id": task_id,
            "review_type": "code-quality",
            "severity": "clean",
            "findings": [],
            "summary": "No issues found",
        }
    )

    # When: Calling review_store with valid JSON
    result = review_store(review_json, db_path=db_path)

    # Then: Should succeed
    assert result == 0

    # Verify row was inserted
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT task_id, review_type, severity, source FROM task_reviews WHERE task_id = ?",
            (task_id,),
        )
        row = cursor.fetchone()

    assert row is not None
    assert row[0] == task_id
    assert row[1] == "code-quality"
    assert row[2] == "clean"
    assert row[3] == "claude"


def test_review_store_invalid_json_returns_error(db_path, repo, capsys):
    """Malformed JSON should return error code."""
    from formaltask.cli.commands.review_store import review_store

    # When: Calling with invalid JSON
    result = review_store("{not valid json}", db_path=db_path)

    # Then: Should return error
    assert result == 1
    captured = capsys.readouterr()
    assert "invalid" in captured.out.lower() or "error" in captured.out.lower()


def test_review_store_invalid_schema_returns_error(db_path, repo, capsys):
    """Valid JSON but invalid schema should return error."""
    from formaltask.cli.commands.review_store import review_store

    # Invalid review_type
    review_json = json.dumps(
        {
            "task_id": 42,
            "review_type": "not-a-real-type",  # Invalid
            "severity": "clean",
            "findings": [],
            "summary": "Test",
        }
    )

    # When: Calling with invalid schema
    result = review_store(review_json, db_path=db_path)

    # Then: Should return error
    assert result == 1
    captured = capsys.readouterr()
    assert "error" in captured.out.lower()


def test_review_store_formatter_path_invalid_json_raises_cli_error(db_path, repo):
    """Formatter path should raise CLIError for invalid JSON."""
    import pytest

    from formaltask.cli.base import CLIError
    from formaltask.cli.commands.review_store import review_store
    from formaltask.cli.exit_codes import ExitCode

    # When: Calling with invalid JSON and formatter (truthy flag)
    with pytest.raises(CLIError) as exc_info:
        review_store("{not valid json}", db_path=db_path, json_mode=True)

    # Then: Should raise CLIError with USAGE_ERROR
    assert exc_info.value.exit_code == ExitCode.USAGE_ERROR
    assert "invalid json" in str(exc_info.value).lower()


def test_review_store_formatter_path_invalid_schema_raises_cli_error(db_path, repo):
    """Formatter path should raise CLIError for invalid schema."""
    import pytest

    from formaltask.cli.base import CLIError
    from formaltask.cli.commands.review_store import review_store
    from formaltask.cli.exit_codes import ExitCode

    # Invalid review_type
    review_json = json.dumps(
        {
            "task_id": 42,
            "review_type": "not-a-real-type",
            "severity": "clean",
            "findings": [],
            "summary": "Test",
        }
    )

    # When: Calling with invalid schema and formatter (truthy flag)
    with pytest.raises(CLIError) as exc_info:
        review_store(review_json, db_path=db_path, json_mode=True)

    # Then: Should raise CLIError with USAGE_ERROR
    assert exc_info.value.exit_code == ExitCode.USAGE_ERROR
    assert "validation error" in str(exc_info.value).lower()


def test_review_store_formatter_path_success_returns_dict(db_path, repo):
    """Formatter path with valid data should return dict structure."""
    from formaltask.cli.commands.review_store import review_store

    # Create epic and task
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test Epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    task_id = repo.create_task("test-epic", "Test task", "Description", ["Criterion 1"])

    # Valid review packet
    review_json = json.dumps(
        {
            "task_id": task_id,
            "review_type": "code-quality",
            "severity": "clean",
            "findings": [],
            "summary": "No issues found",
        }
    )

    # When: Calling review_store with valid JSON and formatter (truthy flag)
    result = review_store(review_json, db_path=db_path, json_mode=True)

    # Then: Should return dict with expected structure
    assert isinstance(result, dict)
    assert result["task_id"] == task_id
    assert result["review_type"] == "code-quality"
    assert result["stored"] is True


def test_cli_review_store_stdin_mode(db_path, repo):
    """Test review-store can read from stdin."""
    import subprocess

    # Create epic and task
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test Epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    task_id = repo.create_task("test-epic", "Test task", "Description", ["Criterion 1"])

    review_json = json.dumps(
        {
            "task_id": task_id,
            "review_type": "code-quality",
            "severity": "clean",
            "findings": [],
            "summary": "All good",
        }
    )

    # When: Calling via subprocess with stdin
    result = subprocess.run(
        ["python3", "-m", "formaltask.cli.pm", "review", "store", "--db-path", str(db_path)],
        input=review_json,
        capture_output=True,
        text=True,
    )

    # Then: Should succeed
    assert result.returncode == 0

    # Verify stored
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT review_type FROM task_reviews WHERE task_id = ?",
            (task_id,),
        )
        row = cursor.fetchone()

    assert row is not None
    assert row[0] == "code-quality"
