"""Tests for complexity refactoring helpers (Task #2005)."""

import pytest


@pytest.fixture
def db_with_commits_table(db_path):
    """Database with commits table and test tasks ready for testing."""
    import sqlite3

    # The commits table is already in schema-v5.sql
    # Create test epic and tasks for foreign key constraint satisfaction
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic for commit tests", "2025-01-01T00:00:00Z"),
        )
        # Create tasks with IDs 1 and 2 for commit_scan tests
        cursor.execute(
            "INSERT INTO tasks (id, epic_name, title, description, created_at) VALUES (?, ?, ?, ?, ?)",
            (1, "test-epic", "Task 1", "Test task 1", "2025-01-01T00:00:00Z"),
        )
        cursor.execute(
            "INSERT INTO tasks (id, epic_name, title, description, created_at) VALUES (?, ?, ?, ?, ?)",
            (2, "test-epic", "Task 2", "Test task 2", "2025-01-01T00:00:00Z"),
        )
        conn.commit()
    return db_path


def test_parse_commits_splits_by_delimiter():
    """Should correctly split commits by record separator."""
    from formaltask.cli.commands.commit_scan import COMMIT_DELIMITER, _parse_commits

    git_output = (
        f"abc123{COMMIT_DELIMITER}Subject 1{COMMIT_DELIMITER}Body 1\n"
        f"def456{COMMIT_DELIMITER}Subject 2{COMMIT_DELIMITER}Body 2"
    )

    commits = _parse_commits(git_output)

    assert len(commits) == 2
    assert commits[0] == ("abc123", "Subject 1", "Body 1")
    assert commits[1] == ("def456", "Subject 2", "Body 2")


def test_parse_commits_handles_empty_output():
    """Should return empty list for empty git output."""
    from formaltask.cli.commands.commit_scan import _parse_commits

    commits = _parse_commits("")

    assert commits == []


def test_parse_commits_handles_multiline_body():
    """Should correctly parse commits with multi-line body."""
    from formaltask.cli.commands.commit_scan import COMMIT_DELIMITER, _parse_commits

    git_output = f"abc123{COMMIT_DELIMITER}Subject line{COMMIT_DELIMITER}Line 1\nLine 2\nLine 3"

    commits = _parse_commits(git_output)

    assert len(commits) == 1
    assert commits[0][0] == "abc123"
    assert commits[0][1] == "Subject line"
    assert commits[0][2] == "Line 1\nLine 2\nLine 3"


@pytest.mark.parametrize(
    "message,expected",
    [
        ("This refs #42 and refs #99", {42, 99}),
        ("This fixes #42 and fixes #99", {42, 99}),
        ("This closes #42", {42}),
        ("Task: #42 - Add new feature", {42}),
    ],
    ids=["refs", "fixes", "closes", "task_colon"],
)
def test_extract_task_refs_finds_keyword_patterns(message, expected):
    """Should find keyword-prefixed task references (refs/fixes/closes/Task:)."""
    from formaltask.cli.commands.commit_scan import _extract_task_refs

    refs = _extract_task_refs(message)

    assert refs == expected


def test_extract_task_refs_finds_bare_hash_pattern():
    """Should find bare '#123' pattern without prefix."""
    from formaltask.cli.commands.commit_scan import _extract_task_refs

    message = "Working on #42 and #99"

    refs = _extract_task_refs(message)

    assert refs == {42, 99}


def test_batch_insert_commit_links_returns_counts(db_with_commits_table):
    """Should return linked_count and skipped_count from batch insert."""
    from formaltask.cli.commands.commit_scan import _batch_insert_commit_links

    db_path = db_with_commits_table
    links = [
        (1, "abc123", "fixes #1 message"),
        (2, "def456", "refs #2 message"),
    ]

    linked, skipped = _batch_insert_commit_links(db_path, links)

    assert linked == 2
    assert skipped == 0


def test_batch_insert_commit_links_skips_duplicates(db_with_commits_table):
    """Should skip duplicates and return skipped_count."""
    from formaltask.cli.commands.commit_scan import _batch_insert_commit_links

    db_path = db_with_commits_table
    links = [(1, "abc123", "first message")]

    # First insert
    linked1, skipped1 = _batch_insert_commit_links(db_path, links)
    assert linked1 == 1
    assert skipped1 == 0

    # Second insert (same commit hash) should be skipped
    linked2, skipped2 = _batch_insert_commit_links(db_path, links)
    assert linked2 == 0
    assert skipped2 == 1
