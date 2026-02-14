"""Test task_list command."""

import pytest

from formaltask.db.connection import DatabaseConnection

# Note: db_path fixture is provided by hooks/tests/conftest.py


@pytest.fixture
def db_with_epic(db_path):
    """Database with 'test-epic' ready for task creation."""
    with DatabaseConnection(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test Epic", "2025-11-01T00:00:00Z"),
        )
    return db_path


# =============================================================================
# Task #2737: New API tests (task_list returns list[dict], raises ValueError)
# =============================================================================


def test_task_list_returns_list_of_dicts(db_with_epic, repo):
    """task_list() always returns list[dict], not int or wrapped dict."""
    from formaltask.cli.commands.task_list import task_list

    repo.create_task("test-epic", "Task 1", "Description 1", ["Criterion 1"])
    repo.create_task("test-epic", "Task 2", "Description 2", ["Criterion 2"])

    # When: Calling task_list
    result = task_list("test-epic", db_path=db_with_epic)

    # Then: Returns list[dict] directly
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], dict)
    assert "id" in result[0]
    assert "title" in result[0]
    assert "status" in result[0]
    assert "started_at" in result[0]
    assert "completed_at" in result[0]


def test_task_list_raises_valueerror_on_epic_not_found(db_path, repo):
    """task_list() raises ValueError when epic not found."""
    from formaltask.cli.commands.task_list import task_list

    with pytest.raises(ValueError, match="not found"):
        task_list("nonexistent-epic", db_path=db_path)


def test_task_list_empty_epic_returns_empty_list(db_path, repo):
    """task_list() returns empty list when epic exists but has no tasks."""
    from formaltask.cli.commands.task_list import task_list

    # Given: Epic with no tasks
    with DatabaseConnection(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("empty-epic", "Empty Epic", "2025-11-01T00:00:00Z"),
        )

    # When: Calling task_list
    result = task_list("empty-epic", db_path=db_path)

    # Then: Should return empty list
    assert isinstance(result, list)
    assert result == []


def test_task_list_filters_by_status(db_with_epic, repo):
    """task_list() filters tasks by status parameter."""
    from formaltask.cli.commands.task_list import task_list

    repo.create_task("test-epic", "Open Task", "Description", ["Criterion 1"])
    task2_id = repo.create_task("test-epic", "Started Task", "Description", ["Criterion 1"])

    # Set task 2 to in_progress
    with DatabaseConnection(db_with_epic) as conn:
        conn.execute("UPDATE tasks SET status = 'in_progress' WHERE id = ?", (task2_id,))

    # When: Filtering by status='open'
    result = task_list("test-epic", db_path=db_with_epic, status="open")

    # Then: Should return only open task
    assert len(result) == 1
    assert result[0]["title"] == "Open Task"
    assert result[0]["status"] == "open"


# =============================================================================
# execute() tests - display concerns (printing, PR lookup)
# =============================================================================


def test_execute_prints_task_list(db_with_epic, repo, capsys, monkeypatch):
    """execute() prints human-readable task list."""
    from argparse import Namespace

    from formaltask.cli.commands import task_list as task_list_module

    # Mock PR lookup to avoid real GitHub API calls
    monkeypatch.setattr(task_list_module, "get_prs_for_tasks", lambda ids: {})

    repo.create_task("test-epic", "Task 1", "Description 1", ["Criterion 1"])
    repo.create_task("test-epic", "Task 2", "Description 2", ["Criterion 2"])

    # When: Calling execute
    args = Namespace(
        epic_name="test-epic", status=None, search=None, json=False, db_path=db_with_epic
    )
    result = task_list_module.execute.__wrapped__(db_with_epic, args)

    # Then: Should print tasks and return 0
    captured = capsys.readouterr()
    assert "Task 1" in captured.out
    assert "Task 2" in captured.out
    assert "Total: 2 tasks" in captured.out
    assert result == 0


def test_execute_json_mode_outputs_structured_data(db_with_epic, repo, capsys, monkeypatch):
    """execute() with JSON mode prints structured output via formatter."""
    import json
    from argparse import Namespace

    from formaltask.cli.commands import task_list as task_list_module

    # Mock PR lookup to avoid real GitHub API calls
    monkeypatch.setattr(task_list_module, "get_prs_for_tasks", lambda ids: {})

    repo.create_task("test-epic", "Task 1", "Description 1", ["Criterion 1"])
    repo.create_task("test-epic", "Task 2", "Description 2", ["Criterion 2"])

    # When: Calling execute with JSON mode
    args = Namespace(
        epic_name="test-epic",
        status=None,
        search=None,
        json=True,
        stream=False,
        db_path=db_with_epic,
    )
    result = task_list_module.execute.__wrapped__(db_with_epic, args)

    # Then: Should print JSON and return 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["success"] is True
    assert "data" in output
    assert output["data"]["total"] == 2
    assert output["data"]["epic_name"] == "test-epic"
    assert len(output["data"]["tasks"]) == 2
    assert result == 0


def test_execute_epic_not_found_prints_error(db_path, repo, capsys, monkeypatch):
    """execute() prints error when epic not found (non-JSON mode)."""
    from argparse import Namespace

    from formaltask.cli.commands import task_list as task_list_module

    # When: Calling execute for non-existent epic
    args = Namespace(epic_name="nonexistent", status=None, search=None, json=False, db_path=db_path)
    result = task_list_module.execute.__wrapped__(db_path, args)

    # Then: Should print error and return 1
    captured = capsys.readouterr()
    assert "Error:" in captured.out
    assert "not found" in captured.out.lower()
    assert result == 1


def test_execute_epic_not_found_json_raises_cli_error(db_path, repo, monkeypatch):
    """execute() raises CLIError when epic not found in JSON mode."""
    from argparse import Namespace

    from formaltask.cli.base import CLIError
    from formaltask.cli.commands import task_list as task_list_module
    from formaltask.cli.exit_codes import ExitCode

    # When: Calling execute for non-existent epic with JSON mode
    args = Namespace(
        epic_name="nonexistent", status=None, search=None, json=True, stream=False, db_path=db_path
    )

    # Then: Should raise CLIError
    with pytest.raises(CLIError) as exc_info:
        task_list_module.execute.__wrapped__(db_path, args)

    assert exc_info.value.exit_code == ExitCode.NOT_FOUND


def test_execute_empty_epic_prints_message(db_path, repo, capsys, monkeypatch):
    """execute() prints message when epic has no tasks."""
    from argparse import Namespace

    from formaltask.cli.commands import task_list as task_list_module

    # Given: Empty epic
    with DatabaseConnection(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("empty-epic", "Empty Epic", "2025-11-01T00:00:00Z"),
        )

    # When: Calling execute
    args = Namespace(epic_name="empty-epic", status=None, search=None, json=False, db_path=db_path)
    result = task_list_module.execute.__wrapped__(db_path, args)

    # Then: Should print "no tasks" message and return 0
    captured = capsys.readouterr()
    assert "No tasks found" in captured.out
    assert result == 0


# =============================================================================
# Task #2181: GitHub PR Utils Integration Tests (in execute)
# =============================================================================


def test_execute_includes_pr_number_from_github_api(db_with_epic, repo, capsys, monkeypatch):
    """execute() adds github_pr_number from get_prs_for_tasks to output."""
    import json
    from argparse import Namespace

    from formaltask.cli.commands import task_list as task_list_module
    from formaltask.git.github import PRInfo

    task_id = repo.create_task("test-epic", "Task 1", "Description", ["Criterion"])

    # Mock get_prs_for_tasks to return PR info
    monkeypatch.setattr(
        task_list_module,
        "get_prs_for_tasks",
        lambda ids: {task_id: PRInfo(number=999, state="OPEN", merged=False)},
    )

    # When: Calling execute with JSON mode
    args = Namespace(
        epic_name="test-epic",
        status=None,
        search=None,
        json=True,
        stream=False,
        db_path=db_with_epic,
    )
    task_list_module.execute.__wrapped__(db_with_epic, args)

    # Then: github_pr_number should come from get_prs_for_tasks
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["data"]["tasks"][0]["github_pr_number"] == 999


def test_execute_human_output_shows_pr_number(db_with_epic, repo, capsys, monkeypatch):
    """Human-readable output should include PR number when available."""
    from argparse import Namespace

    from formaltask.cli.commands import task_list as task_list_module
    from formaltask.git.github import PRInfo

    task_id = repo.create_task("test-epic", "Task 1", "Description", ["Criterion"])

    # Mock get_prs_for_tasks to return PR info
    monkeypatch.setattr(
        task_list_module,
        "get_prs_for_tasks",
        lambda ids: {task_id: PRInfo(number=42, state="OPEN", merged=False)},
    )

    # When: Calling execute (non-JSON mode)
    args = Namespace(
        epic_name="test-epic", status=None, search=None, json=False, db_path=db_with_epic
    )
    task_list_module.execute.__wrapped__(db_with_epic, args)

    # Then: Human output should show PR number
    captured = capsys.readouterr()
    assert "PR#42" in captured.out


def test_execute_filters_by_status_prints_filtered_results(db_with_epic, repo, capsys, monkeypatch):
    """execute() passes status filter and prints filtered results."""
    from argparse import Namespace

    from formaltask.cli.commands import task_list as task_list_module

    monkeypatch.setattr(task_list_module, "get_prs_for_tasks", lambda ids: {})

    repo.create_task("test-epic", "Open Task", "Description", ["Criterion 1"])
    task2_id = repo.create_task("test-epic", "Started Task", "Description", ["Criterion 1"])
    task3_id = repo.create_task("test-epic", "Completed Task", "Description", ["Criterion 1"])

    # Set task 2 to in_progress
    with DatabaseConnection(db_with_epic) as conn:
        conn.execute("UPDATE tasks SET status = 'in_progress' WHERE id = ?", (task2_id,))

    # Complete task 3
    with DatabaseConnection(db_with_epic) as conn:
        conn.execute(
            "UPDATE tasks SET completed_at = ?, status = 'completed' WHERE id = ?",
            ("2025-11-02T00:00:00Z", task3_id),
        )
        conn.execute(
            "INSERT INTO commits (task_id, commit_hash, commit_message) VALUES (?, ?, ?)",
            (task3_id, "abc123", "Test commit"),
        )

    # When: Filtering by status='open'
    args = Namespace(
        epic_name="test-epic", status="open", search=None, json=False, db_path=db_with_epic
    )
    task_list_module.execute.__wrapped__(db_with_epic, args)

    # Then: Should show only open task
    captured = capsys.readouterr()
    assert "Open Task" in captured.out
    assert "Started Task" not in captured.out
    assert "Completed Task" not in captured.out
    assert "Total: 1 tasks" in captured.out
