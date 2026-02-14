"""CLI test fixtures.

Shared fixtures for CLI tests to reduce duplication.
"""

import subprocess

import pytest

from formaltask.epics import create_epic


@pytest.fixture
def db_with_epic(db_path):
    """Database with schema and a pre-created epic.

    Uses db_path fixture which already handles schema and migration tracking.
    """
    create_epic(db_path=db_path, name="test-epic", description="Test epic")
    return db_path


@pytest.fixture
def git_repo_with_commit(tmp_path):
    """Git repo with one commit.

    Returns:
        tuple: (repo_path, commit_hash)
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    (repo / "file.txt").write_text("content")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return repo, result.stdout.strip()
