"""Tests for simplified task_complete command (no GPT review).

Note: --force flag was removed in Task #2273. Tests now add clean reviews
in setup to satisfy mandatory review gates.
"""


def test_completes_task_without_review(db_path, repo, mock_review_gates):
    """Test that task is completed with pre-existing clean reviews.

    Simplified task_complete should:
    1. Scan commits
    2. Validate evidence
    3. Check review gates (added Task #2222) - mocked in this test
    4. Update status to 'completed'
    """
    from formaltask.cli.commands.task_complete import task_complete
    from formaltask.db.connection import DatabaseConnection

    # Insert test task with commit (for evidence)
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO tasks (epic_name, title, description, position, status, created_at, started_at)
               VALUES ('master-adhoc', 'Test Task', 'Test', 0, 'in_progress', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')"""
        )
        task_id = cursor.lastrowid
        cursor.execute(
            """INSERT INTO commits (task_id, commit_hash, commit_message)
               VALUES (?, 'abc123', 'Test commit')""",
            (task_id,),
        )
        conn.commit()

    # Run task_complete WITHOUT code_review_runner
    task_complete(
        task_id=task_id,
        db_path=db_path,
    )

    # Verify: Task status is 'completed'
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, completed_at FROM tasks WHERE id = ?", (task_id,))
        result = cursor.fetchone()

    assert result[0] == "completed", f"Expected status 'completed', got '{result[0]}'"
    assert result[1] is not None, "completed_at should be set"


def test_completion_records_sha_in_git_repo(db_path, repo, monkeypatch, mock_review_gates):
    """SHA is recorded when completing task in git repo."""
    from formaltask.cli.commands.task_complete import task_complete
    from formaltask.db.connection import DatabaseConnection

    expected_sha = "abc123def456789012345678901234567890abcd"  # pragma: allowlist secret

    # Mock get_head_sha to return known SHA.
    # This works because _complete_task() uses late import (inside function body),
    # so the patch is applied before the import happens at call time.
    monkeypatch.setattr("formaltask.git.utils.get_head_sha", lambda: expected_sha)

    # Insert test task with commit
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO tasks (epic_name, title, description, position, status, created_at, started_at)
               VALUES ('master-adhoc', 'Test Task', 'Test', 0, 'in_progress', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')"""
        )
        task_id = cursor.lastrowid
        cursor.execute(
            """INSERT INTO commits (task_id, commit_hash, commit_message)
               VALUES (?, 'abc123', 'Test commit')""",
            (task_id,),
        )
        conn.commit()

    # Run task_complete without force (Task #2273 removed --force)
    task_complete(
        task_id=task_id,
        db_path=db_path,
    )

    # Verify: head_commit_sha is recorded
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT head_commit_sha FROM tasks WHERE id = ?", (task_id,))
        result = cursor.fetchone()

    assert result[0] == expected_sha, f"Expected SHA '{expected_sha}', got '{result[0]}'"


def test_completion_records_null_outside_git_repo(db_path, repo, monkeypatch, mock_review_gates):
    """NULL recorded when completing task outside git repo."""
    from formaltask.cli.commands.task_complete import task_complete
    from formaltask.db.connection import DatabaseConnection

    # Mock get_head_sha to return None (simulates non-git directory)
    monkeypatch.setattr("formaltask.git.utils.get_head_sha", lambda: None)

    # Insert test task with commit
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO tasks (epic_name, title, description, position, status, created_at, started_at)
               VALUES ('master-adhoc', 'Test Task', 'Test', 0, 'in_progress', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')"""
        )
        task_id = cursor.lastrowid
        cursor.execute(
            """INSERT INTO commits (task_id, commit_hash, commit_message)
               VALUES (?, 'abc123', 'Test commit')""",
            (task_id,),
        )
        conn.commit()

    # Run task_complete without force (Task #2273 removed --force)
    task_complete(
        task_id=task_id,
        db_path=db_path,
    )

    # Verify: head_commit_sha is NULL
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT head_commit_sha FROM tasks WHERE id = ?", (task_id,))
        result = cursor.fetchone()

    assert result[0] is None, f"Expected NULL, got '{result[0]}'"


