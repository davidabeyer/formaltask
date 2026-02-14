"""Test CLI commit-link command."""

import sqlite3
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.paths import SCHEMA_FILE


def _create_db_with_schema(db_path: Path) -> None:
    """Create database with schema."""
    with sqlite3.connect(db_path) as conn:
        with open(SCHEMA_FILE) as f:
            conn.executescript(f.read())
        conn.commit()


@pytest.fixture
def test_db(tmp_path):
    """Create test database with epic and tasks."""
    from formaltask.epics import create_epic
    from formaltask.tasks.crud import create_task

    db_path = tmp_path / "test.db"
    _create_db_with_schema(db_path)
    create_epic(db_path=str(db_path), name="test-epic", description="Test epic")
    create_task(
        db_path=str(db_path),
        epic_name="test-epic",
        title="Task 1",
        description="Description 1",
        criteria=["Criterion 1"],
    )
    create_task(
        db_path=str(db_path),
        epic_name="test-epic",
        title="Task 2",
        description="Description 2",
        criteria=["Criterion 2"],
    )

    return db_path


@pytest.fixture
def git_repo(tmp_path):
    """Create temporary git repo with test commits."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)

    test_file = repo_path / "test.txt"
    test_file.write_text("First commit")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "fix: Fix bug"], cwd=repo_path, check=True, capture_output=True
    )

    return repo_path


def _get_commit_hash(repo_path: Path, ref: str = "HEAD") -> str:
    """Get commit hash from git repo."""
    result = subprocess.run(
        ["git", "rev-parse", ref], cwd=repo_path, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def test_link_commit_to_task_success(test_db, git_repo):
    """Test successfully linking a commit to a task."""
    from formaltask.cli.commands.commit_link import commit_link

    commit_hash = _get_commit_hash(git_repo)

    result = commit_link(
        task_id=1, commit_hash=commit_hash, db_path=str(test_db), repo_path=str(git_repo)
    )

    assert result["linked"] is True
    assert result["task_id"] == 1
    assert result["commit_hash"] == commit_hash

    # Verify in database
    with sqlite3.connect(test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT task_id, commit_hash FROM commits WHERE task_id = 1")
        row = cursor.fetchone()

    assert row is not None
    assert row[0] == 1
    assert row[1] == commit_hash


def test_rejects_nonexistent_task(test_db, git_repo):
    """Test that linking to non-existent task raises error."""
    from formaltask.cli.base import CLIError
    from formaltask.cli.commands.commit_link import commit_link

    commit_hash = _get_commit_hash(git_repo)

    with pytest.raises(CLIError, match="Task.*not found"):
        commit_link(
            task_id=999, commit_hash=commit_hash, db_path=str(test_db), repo_path=str(git_repo)
        )


def test_rejects_invalid_commit_hash(test_db, git_repo):
    """Test that invalid commit hash raises error."""
    from formaltask.cli.base import CLIError
    from formaltask.cli.commands.commit_link import commit_link

    with pytest.raises(CLIError, match="Commit.*not found"):
        commit_link(
            task_id=1,
            commit_hash="deadbeef1234567890abcdef1234567890abcdef",  # pragma: allowlist secret
            db_path=str(test_db),
            repo_path=str(git_repo),
        )


def test_duplicate_link_skips_gracefully(test_db, git_repo):
    """Test that duplicate link is handled gracefully (skipped)."""
    from formaltask.cli.commands.commit_link import commit_link

    commit_hash = _get_commit_hash(git_repo)

    # First link
    result1 = commit_link(
        task_id=1, commit_hash=commit_hash, db_path=str(test_db), repo_path=str(git_repo)
    )
    assert result1["linked"] is True

    # Second link (duplicate)
    result2 = commit_link(
        task_id=1, commit_hash=commit_hash, db_path=str(test_db), repo_path=str(git_repo)
    )
    assert result2["linked"] is False
    assert result2.get("skipped") is True

    # Verify only one record exists
    with sqlite3.connect(test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM commits WHERE task_id = 1")
        count = cursor.fetchone()[0]

    assert count == 1


def test_cli_command_success(test_db, git_repo):
    """Test CLI command execution."""
    commit_hash = _get_commit_hash(git_repo)

    result = subprocess.run(
        [
            "python3",
            "-m",
            "formaltask.cli.pm",
            "commit-link",
            "1",
            commit_hash,
            "--db-path",
            str(test_db),
            "--repo-path",
            str(git_repo),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "linked" in result.stdout.lower()


def test_rejects_empty_commit_hash(test_db):
    """Test that empty commit hash raises error."""
    from formaltask.cli.base import CLIError
    from formaltask.cli.commands.commit_link import commit_link

    with pytest.raises(CLIError, match="cannot be empty"):
        commit_link(task_id=1, commit_hash="", db_path=str(test_db), repo_path=None)


def test_rejects_nonexistent_repo_path(test_db, tmp_path):
    """Test that non-existent repo path raises error."""
    from formaltask.cli.base import CLIError
    from formaltask.cli.commands.commit_link import commit_link

    fake_path = str(tmp_path / "nonexistent_repo")

    with pytest.raises(CLIError, match="does not exist"):
        commit_link(task_id=1, commit_hash="abc123", db_path=str(test_db), repo_path=fake_path)


def test_custom_message_overrides_git_message(test_db, git_repo):
    """Test that --message flag overrides git commit message."""
    from formaltask.cli.commands.commit_link import commit_link

    commit_hash = _get_commit_hash(git_repo)
    custom_message = "Custom override message"

    result = commit_link(
        task_id=1,
        commit_hash=commit_hash,
        db_path=str(test_db),
        repo_path=str(git_repo),
        message=custom_message,
    )

    assert result["linked"] is True
    assert result["commit_message"] == custom_message

    # Verify in database
    with sqlite3.connect(test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT commit_message FROM commits WHERE task_id = 1")
        row = cursor.fetchone()

    assert row[0] == custom_message
