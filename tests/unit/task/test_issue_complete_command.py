"""Tests for pm-task-complete command.

Following TDD approach: write test first, then implement.
"""

import sqlite3

import pytest

# Note: db_path fixture is provided by hooks/tests/conftest.py


def test_task_complete_validates_evidence_required(db_path, repo, tmp_path, monkeypatch):
    """Test task_complete() validates task has commits before completion."""
    # Given: A started task WITHOUT commits but WITH review passed
    from formaltask.cli.commands.task_complete import task_complete
    from formaltask.tasks.guards import GuardViolation
    from formaltask.tasks.lifecycle import transition_task_status

    # Create epic
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    # Create and start task (no commits linked)
    task_id = repo.create_task("test-epic", "Test task", "Description", ["Criterion 1"])
    # Transition to in_progress using the state machine
    transition_task_status(db_path, task_id, "in_progress")

    # Isolate from real git repo - set GIT_REPO_PATH to non-git directory
    monkeypatch.setenv("GIT_REPO_PATH", str(tmp_path))

    # When/Then: Completing task without commits raises GuardViolation
    with pytest.raises(GuardViolation, match="evidence required"):
        task_complete(task_id, db_path=db_path)


def test_task_complete_succeeds_with_commits(db_path, repo, mock_review_gates):
    """Test task_complete() succeeds when task has commits."""
    # Given: A started task WITH commits AND review passed
    from formaltask.cli.commands.task_complete import task_complete
    from formaltask.tasks.lifecycle import transition_task_status

    # Create epic
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    # Create and start task
    task_id = repo.create_task("test-epic", "Test task", "Description", ["Criterion 1"])
    # Transition to in_progress using the state machine
    transition_task_status(db_path, task_id, "in_progress")

    # Link a commit to provide evidence
    repo.link_commit(task_id, "abc123", "Test commit message")

    # When: Completing task with commits
    task_complete(task_id, db_path=db_path)

    # Then: Task should be completed
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, completed_at FROM tasks WHERE id = ?", (task_id,))
        result = cursor.fetchone()

    assert result[0] == "completed"
    assert result[1] is not None  # completed_at timestamp set


def test_task_complete_shows_newly_unblocked_tasks(db_path, repo, capsys, mock_review_gates):
    """Test task_complete() shows tasks that become unblocked after completion."""
    from formaltask.cli.commands.task_complete import task_complete
    from formaltask.tasks.lifecycle import transition_task_status

    # Create epic
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    # Create task 1 (no dependencies)
    task1_id = repo.create_task("test-epic", "Foundation task", "Foundation", ["Criterion 1"])

    # Create task 2 (depends on task 1)
    task2_id = repo.create_task(
        "test-epic", "Dependent task", "Depends on task 1", ["Criterion 2"], depends_on=[task1_id]
    )

    # Start task 1 and add commit
    transition_task_status(db_path, task1_id, "in_progress")
    repo.link_commit(task1_id, "abc123", "Foundation commit")

    # Complete task 1
    task_complete(task1_id, db_path=db_path)

    # Capture stdout and verify exact output format
    captured = capsys.readouterr()

    # Assert exact header format from task_complete
    assert "✅ Tasks now ready (unblocked):" in captured.out, (
        f"Expected exact header '✅ Tasks now ready (unblocked):'. Got: {captured.out}"
    )

    # Assert specific task format: "   #{task_id}: {title}"
    import re

    task_line_pattern = rf"^\s*#{task2_id}: Dependent task"
    assert re.search(task_line_pattern, captured.out, re.MULTILINE), (
        f"Expected task line matching '   #{task2_id}: Dependent task'. Got: {captured.out}"
    )


def test_task_complete_shows_still_blocked_tasks(db_path, repo, capsys, mock_review_gates):
    """Test task_complete() shows tasks that are still blocked with reasons."""
    from formaltask.cli.commands.task_complete import task_complete
    from formaltask.tasks.lifecycle import transition_task_status

    # Create epic
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    # Create task 1 (no dependencies)
    task1_id = repo.create_task("test-epic", "Task A", "First task", ["Criterion 1"])

    # Create task 2 (no dependencies)
    task2_id = repo.create_task("test-epic", "Task B", "Second task", ["Criterion 2"])

    # Create task 3 (depends on BOTH task 1 and task 2)
    task3_id = repo.create_task(
        "test-epic",
        "Task C needs both",
        "Depends on both",
        ["Criterion 3"],
        depends_on=[task1_id, task2_id],
    )

    # Start task 1 and add commit
    transition_task_status(db_path, task1_id, "in_progress")
    repo.link_commit(task1_id, "abc123", "Task A commit")

    # Complete task 1 (task 3 should still be blocked because task 2 isn't done)
    task_complete(task1_id, db_path=db_path)

    # Capture stdout and check output mentions still-blocked task
    captured = capsys.readouterr()
    assert "blocked" in captured.out.lower(), (
        f"Expected output to mention blocked tasks. Got: {captured.out}"
    )
    assert str(task3_id) in captured.out or "Task C" in captured.out, (
        f"Expected output to mention task {task3_id}. Got: {captured.out}"
    )


def test_task_complete_handles_invalid_json_in_depends_on(db_path, repo, capsys, mock_review_gates):
    """Test task_complete() gracefully handles invalid JSON in depends_on field."""
    from formaltask.cli.commands.task_complete import task_complete
    from formaltask.tasks.lifecycle import transition_task_status

    # Create epic
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    # Create task 1 (will be completed)
    task1_id = repo.create_task("test-epic", "Task A", "First task", ["Criterion 1"])

    # Create task 2 and manually set invalid JSON in depends_on
    task2_id = repo.create_task("test-epic", "Task B corrupted", "Has bad JSON", ["Criterion 2"])

    # Corrupt the depends_on field with invalid JSON
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tasks SET depends_on = ? WHERE id = ?", ("not valid json at all", task2_id)
        )
        conn.commit()

    # Start task 1 and add commit
    transition_task_status(db_path, task1_id, "in_progress")
    repo.link_commit(task1_id, "abc123", "Task A commit")

    # Complete task 1 - should NOT crash despite corrupted depends_on in task 2
    task_complete(task1_id, db_path=db_path)

    # Verify task 1 was completed successfully
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM tasks WHERE id = ?", (task1_id,))
        result = cursor.fetchone()

    assert result[0] == "completed", "Task should be completed despite invalid JSON in other task"


def test_task_complete_no_evidence_flag_bypasses_guard(
    db_path, repo, tmp_path, monkeypatch, mock_review_gates
):
    """Test --no-evidence flag bypasses the evidence guard for audit/doc tasks."""
    from formaltask.cli.commands.task_complete import task_complete
    from formaltask.tasks.lifecycle import transition_task_status

    # Create epic
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    # Create and start task WITHOUT commits (audit task scenario)
    task_id = repo.create_task("test-epic", "Audit task", "No code changes", ["Audit complete"])
    transition_task_status(db_path, task_id, "in_progress")

    # Isolate from real git repo
    monkeypatch.setenv("GIT_REPO_PATH", str(tmp_path))

    # When: Completing with no_evidence=True
    result = task_complete(task_id, db_path=db_path, no_evidence=True)

    # Then: Task should be completed (guard bypassed)
    assert result == 0
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        status = cursor.fetchone()[0]
    assert status == "completed"


def test_task_complete_cli_no_evidence_flag_accepted(
    db_path, repo, tmp_path, monkeypatch, mock_review_gates
):
    """Test --no-evidence CLI flag is parsed and passed to task_complete()."""
    import sys

    from formaltask.tasks.lifecycle import transition_task_status

    # Create epic and task
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    task_id = repo.create_task("test-epic", "Audit task", "No code", ["Done"])
    transition_task_status(db_path, task_id, "in_progress")

    # Isolate from git
    monkeypatch.setenv("GIT_REPO_PATH", str(tmp_path))

    # Run CLI with --no-evidence flag
    from formaltask.cli import pm

    monkeypatch.setattr(
        sys,
        "argv",
        ["pm", "task", "complete", str(task_id), "--no-evidence", "--db-path", str(db_path)],
    )

    result = pm.main()

    assert result == 0

    # Verify task completed
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        status = cursor.fetchone()[0]
    assert status == "completed"


def test_task_complete_raises_error_when_task_not_found(db_path, repo):
    """Test task_complete() raises CLIError when task does not exist.

    Task #1585: Return CLIError instead of silently continuing when task is None.
    """
    from formaltask.cli.base import CLIError
    from formaltask.cli.commands.task_complete import task_complete
    from formaltask.cli.exit_codes import ExitCode

    # Given: A task ID that does not exist
    nonexistent_task_id = 99999

    # When/Then: Calling task_complete should raise CLIError with NOT_FOUND exit code
    with pytest.raises(CLIError) as exc_info:
        task_complete(nonexistent_task_id, db_path=db_path)

    # Verify error details
    error = exc_info.value
    assert error.exit_code == ExitCode.NOT_FOUND
    assert "99999" in error.message
    assert "not found" in error.message.lower()


def test_tasks_without_dependencies_not_marked_newly_ready(
    db_path, repo, capsys, mock_review_gates
):
    """Test tasks with NO dependencies are NOT marked as 'newly ready'.

    Task #1596: Add check `if task.depends_on:` before marking 'newly ready'.
    Tasks that never had dependencies should not appear in the unblocked list
    since they were never blocked in the first place.
    """
    from formaltask.cli.commands.task_complete import task_complete
    from formaltask.tasks.lifecycle import transition_task_status

    # Create epic
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    # Create task 1 (no dependencies) - will be completed
    task1_id = repo.create_task("test-epic", "Task A", "First task", ["Criterion 1"])

    # Create task 2 (no dependencies) - should NOT be shown as "newly ready"
    task2_id = repo.create_task("test-epic", "Task B no deps", "Second task", ["Criterion 2"])

    # Start task 1 and add commit
    transition_task_status(db_path, task1_id, "in_progress")
    repo.link_commit(task1_id, "abc123", "Task A commit")

    # Complete task 1
    task_complete(task1_id, db_path=db_path)

    # Capture output
    captured = capsys.readouterr()

    # Task 2 has NO dependencies, so it should NOT appear in "newly ready" list
    # The "newly ready" message should not contain task 2
    if "Tasks now ready" in captured.out or "unblocked" in captured.out.lower():
        assert str(task2_id) not in captured.out, (
            f"Task #{task2_id} with no dependencies should NOT appear in newly ready list. "
            f"Output: {captured.out}"
        )
        assert "Task B no deps" not in captured.out, (
            f"Task B (no deps) should NOT appear in newly ready list. Output: {captured.out}"
        )


def test_completion_evidence_flag_sets_field_and_bypasses_guard(
    db_path, repo, tmp_path, monkeypatch, mock_review_gates
):
    """Test --completion-evidence flag sets field and satisfies evidence guard.

    Task #1893: Add completion_evidence field for already-done tasks.
    The flag should:
    1. Set the completion_evidence field in the database
    2. Allow task completion without commits (evidence guard accepts completion_evidence)
    """
    import sys

    from formaltask.tasks.lifecycle import transition_task_status

    # Create epic and task
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    task_id = repo.create_task(
        "test-epic", "Already done task", "Work completed before agent", ["Done"]
    )
    transition_task_status(db_path, task_id, "in_progress")

    # Isolate from real git repo
    monkeypatch.setenv("GIT_REPO_PATH", str(tmp_path))

    # Run CLI with --completion-evidence flag
    from formaltask.cli import pm

    evidence_text = "Work was already completed by previous agent - verified tests pass"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pm",
            "task", "complete",
            str(task_id),
            "--completion-evidence",
            evidence_text,
            "--db-path",
            str(db_path),
        ],
    )

    result = pm.main()

    # Then: Task should be completed
    assert result == 0, "task-complete with --completion-evidence should succeed"

    # And: completion_evidence field should be set
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, completion_evidence FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        status, completion_evidence = row

    assert status == "completed", "Task should be in completed status"
    assert completion_evidence == evidence_text, (
        f"completion_evidence should be set to provided text, got: {completion_evidence}"
    )


def test_completion_evidence_warns_if_local_git_changes_exist(
    db_path, repo, tmp_path, monkeypatch, capsys, mock_review_gates
):
    """Test --completion-evidence warns when local uncommitted changes exist.

    Task #1893: Check for local git changes to distinguish 'did work' from 'work already done'.
    If local changes exist, agent probably did work and should commit instead of claiming
    pre-existing work with completion_evidence.
    """
    import subprocess

    from formaltask.tasks.lifecycle import transition_task_status

    # Create epic and task
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

    task_id = repo.create_task("test-epic", "Task with local changes", "Test", ["Done"])
    transition_task_status(db_path, task_id, "in_progress")

    # Create a git repo with uncommitted changes
    git_dir = tmp_path / "git_repo"
    git_dir.mkdir()
    subprocess.run(["git", "init"], cwd=git_dir, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=git_dir, capture_output=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=git_dir, capture_output=True)

    # Create a committed file first (need at least one commit)
    initial_file = git_dir / "initial.txt"
    initial_file.write_text("Initial content")
    subprocess.run(["git", "add", "initial.txt"], cwd=git_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=git_dir, capture_output=True)

    # Create uncommitted local changes
    new_file = git_dir / "new_work.py"
    new_file.write_text("# New work done by agent")

    # Set GIT_REPO_PATH to our test git repo
    monkeypatch.setenv("GIT_REPO_PATH", str(git_dir))

    # Use task_complete directly with completion_evidence
    from formaltask.cli.commands.task_complete import task_complete

    evidence_text = "Work was already done"
    result = task_complete(
        task_id,
        db_path=db_path,
        completion_evidence=evidence_text,
    )

    # Should still complete (warning doesn't block)
    assert result == 0, "task_complete should succeed"

    # Capture output and verify warning about local changes
    captured = capsys.readouterr()
    assert "uncommitted" in captured.out.lower() or "local changes" in captured.out.lower(), (
        f"Expected warning about uncommitted/local changes. Got: {captured.out}"
    )
