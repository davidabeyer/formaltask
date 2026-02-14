"""Tests for utility command JSON output (Task #1384).

Tests for commit-scan, commit-link with OutputFormatter support.
Follows TDD workflow - tests written before implementation.

Task #2649: Removed ready-tasks tests (command deleted).
"""

import json
import subprocess


def test_commit_scan_json_returns_counts(db_path, repo, tmp_path):
    """Test that commit-scan with --json returns {"data": {"linked_count": N, "skipped_count": N}}."""
    repo.create_epic("test-epic", "Test epic")
    repo.create_task("test-epic", "Task A", "First task", ["Done"])

    # Run commit-scan with --json (on tmp_path which is not a git repo, so 0 results)
    result = subprocess.run(
        [
            "python3",
            "-m",
            "formaltask.cli.pm",
            "--json",
            "commit-scan",
            "--db-path",
            str(db_path),
            "--repo-path",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"

    response = json.loads(result.stdout)
    assert response.get("success") is True
    assert "data" in response
    assert "linked_count" in response["data"]
    assert "skipped_count" in response["data"]
    assert isinstance(response["data"]["linked_count"], int)
    assert isinstance(response["data"]["skipped_count"], int)


def test_commit_link_json_returns_linked(db_path, repo, git_repo_with_commit):
    """Test that commit-link with --json returns {"data": {"linked": true, ...}}."""
    repo.create_epic("test-epic", "Test epic")
    task_id = repo.create_task("test-epic", "Task A", "First task", ["Done"])

    git_repo, commit_hash = git_repo_with_commit

    # Run commit-link with --json
    result = subprocess.run(
        [
            "python3",
            "-m",
            "formaltask.cli.pm",
            "--json",
            "commit-link",
            str(task_id),
            commit_hash,
            "--db-path",
            str(db_path),
            "--repo-path",
            str(git_repo),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"

    response = json.loads(result.stdout)
    assert response.get("success") is True
    assert "data" in response
    assert response["data"]["linked"] is True
    assert response["data"]["task_id"] == task_id
    assert response["data"]["commit_hash"] == commit_hash


def test_commit_link_json_error_task_not_found(db_path, repo, git_repo_with_commit):
    """Test that commit-link with --json returns JSON error when task not found."""
    git_repo, commit_hash = git_repo_with_commit

    # Run commit-link with non-existent task ID
    result = subprocess.run(
        [
            "python3",
            "-m",
            "formaltask.cli.pm",
            "--json",
            "commit-link",
            "99999",  # Non-existent task
            commit_hash,
            "--db-path",
            str(db_path),
            "--repo-path",
            str(git_repo),
        ],
        capture_output=True,
        text=True,
    )

    # Should return non-zero exit code
    assert result.returncode != 0

    # stdout should be valid JSON with error info
    response = json.loads(result.stdout)
    assert response.get("success") is False
    assert "error" in response
    assert "message" in response["error"]


def test_commit_scan_json_error_invalid_date(db_path, repo, tmp_path):
    """Test that commit-scan with --json returns JSON error for invalid date format."""
    # Run commit-scan with invalid date format
    result = subprocess.run(
        [
            "python3",
            "-m",
            "formaltask.cli.pm",
            "--json",
            "commit-scan",
            "--db-path",
            str(db_path),
            "--repo-path",
            str(tmp_path),
            "--since",
            "invalid-date",  # Invalid date format
        ],
        capture_output=True,
        text=True,
    )

    # Should return non-zero exit code
    assert result.returncode != 0

    # stdout should be valid JSON with error info
    response = json.loads(result.stdout)
    assert response.get("success") is False
    assert "error" in response
    assert "message" in response["error"]
    assert "Invalid date format" in response["error"]["message"]
