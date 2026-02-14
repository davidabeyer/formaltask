"""Tests for pm epic-health command.

Following TDD approach: write tests first, then implement.
Task #1786: Add epic-health CLI command.
"""


def test_execute_returns_zero_for_healthy_epic(db_path, repo):
    """Test execute returns 0 for epic with no dependency issues."""
    import argparse

    from formaltask.cli.commands import epic_health

    repo.create_epic("healthy-epic", "Test epic")
    repo.create_task("healthy-epic", "Task 1", "Description", ["Criterion"])

    args = argparse.Namespace(epic_name="healthy-epic", db_path=db_path)
    result = epic_health.execute(args)

    assert result == 0


def test_execute_returns_nonzero_for_issues(db_path, repo):
    """Test execute returns GENERAL_ERROR when issues found."""
    import argparse
    import json
    import sqlite3

    from formaltask.cli.commands import epic_health
    from formaltask.cli.exit_codes import ExitCode

    repo.create_epic("unhealthy-epic", "Test epic")
    task1_id = repo.create_task("unhealthy-epic", "Task 1", "Description", ["Criterion"])
    task2_id = repo.create_task("unhealthy-epic", "Task 2", "Description", ["Criterion"])

    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE tasks SET status = 'cancelled' WHERE id = ?", (task1_id,))
        conn.execute(
            "UPDATE tasks SET depends_on = ? WHERE id = ?",
            (json.dumps([task1_id]), task2_id),
        )

    args = argparse.Namespace(epic_name="unhealthy-epic", db_path=db_path)
    result = epic_health.execute(args)

    assert result == ExitCode.GENERAL_ERROR


def test_epic_health_shows_healthy_epic(db_path, repo):
    """Test epic-health shows healthy message for epic with no issues."""
    import subprocess
    import sys

    repo.create_epic("healthy-epic", "Test epic")
    repo.create_task("healthy-epic", "Task 1", "Description", ["Criterion"])

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "epic", "health",
            "healthy-epic",
            "--db-path",
            db_path,
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "healthy" in result.stdout.lower()


def test_epic_health_shows_orphaned_dependencies(db_path, repo):
    """Test epic-health shows orphaned dependency issues."""
    import json
    import sqlite3
    import subprocess
    import sys

    repo.create_epic("test-epic", "Test epic")
    task1_id = repo.create_task("test-epic", "Task 1", "Description", ["Criterion"])
    task2_id = repo.create_task("test-epic", "Task 2", "Description", ["Criterion"])

    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE tasks SET status = 'cancelled' WHERE id = ?", (task1_id,))
        conn.execute(
            "UPDATE tasks SET depends_on = ? WHERE id = ?",
            (json.dumps([task1_id]), task2_id),
        )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "epic", "health",
            "test-epic",
            "--db-path",
            db_path,
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert str(task2_id) in result.stdout
    assert "cancelled" in result.stdout.lower()


def test_epic_health_epic_not_found(db_path, repo):
    """Test epic-health shows error for non-existent epic."""
    import subprocess
    import sys

    from formaltask.cli.exit_codes import ExitCode

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "epic", "health",
            "nonexistent-epic",
            "--db-path",
            db_path,
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == ExitCode.NOT_FOUND
    output = result.stdout.lower() + result.stderr.lower()
    assert "not found" in output or "does not exist" in output


def test_epic_health_empty_epic(db_path, repo):
    """Test epic-health shows success for empty epic."""
    import subprocess
    import sys

    repo.create_epic("empty-epic", "Empty test epic")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "epic", "health",
            "empty-epic",
            "--db-path",
            db_path,
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "healthy" in result.stdout.lower()


def test_epic_health_shows_cross_epic_warning(db_path, repo):
    """Test epic-health shows cross-epic dependency warning."""
    import json
    import sqlite3
    import subprocess
    import sys

    repo.create_epic("epic-a", "First epic")
    repo.create_epic("epic-b", "Second epic")
    task_in_a = repo.create_task("epic-a", "Task in A", "Description", ["Criterion"])
    task_in_b = repo.create_task("epic-b", "Task in B", "Description", ["Criterion"])

    # Make task in epic-b depend on task in epic-a (cross-epic)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET depends_on = ? WHERE id = ?",
            (json.dumps([task_in_a]), task_in_b),
        )

    result = subprocess.run(
        [sys.executable, "-m", "formaltask.cli.pm", "epic", "health", "epic-b", "--db-path", db_path],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "cross-epic" in result.stdout.lower()
    assert str(task_in_b) in result.stdout


def test_epic_health_json_output_healthy(db_path, repo):
    """Test epic-health returns valid JSON with --json flag."""
    import json
    import subprocess
    import sys

    repo.create_epic("json-test-epic", "Test epic")
    repo.create_task("json-test-epic", "Task 1", "Description", ["Criterion"])

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "--json",
            "epic", "health",
            "json-test-epic",
            "--db-path",
            db_path,
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["success"] is True
    assert data["data"]["epic_name"] == "json-test-epic"
    assert data["data"]["healthy"] is True
    assert data["data"]["issues"] == []
