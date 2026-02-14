"""Tests for --search flag in task-list command (Task #2651).

TDD: Write tests first, then implement.
Merges task-search functionality into task-list with --search flag.
"""


def test_task_list_search_filters_by_title(db_path, repo):
    """Test that search parameter filters tasks by title."""
    from formaltask.cli.commands.task_list import task_list

    repo.create_epic("test-epic", "Test epic")
    repo.create_task("test-epic", "Implement login flow", "Description", ["C1"])
    repo.create_task("test-epic", "Add logout button", "Description", ["C1"])
    repo.create_task("test-epic", "Fix database bug", "Description", ["C1"])

    # When: Listing tasks with search filter
    result = task_list("test-epic", db_path=db_path, search="login")

    # Then: Should only return matching tasks
    assert isinstance(result, list)
    assert len(result) == 1
    assert "login" in result[0]["title"].lower()


def test_task_list_search_filters_by_description(db_path, repo):
    """Test that search parameter also matches task description."""
    from formaltask.cli.commands.task_list import task_list

    repo.create_epic("test-epic", "Test epic")
    # Task with auth in description but not title
    repo.create_task("test-epic", "Generic task", "Handle authentication flow", ["C1"])
    repo.create_task("test-epic", "Other task", "Unrelated description", ["C1"])

    # When: Listing tasks with search filter
    result = task_list("test-epic", db_path=db_path, search="authentication")

    # Then: Should find task by description
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["title"] == "Generic task"


def test_task_list_search_case_insensitive(db_path, repo):
    """Test that search is case insensitive."""
    from formaltask.cli.commands.task_list import task_list

    repo.create_epic("test-epic", "Test epic")
    repo.create_task("test-epic", "Implement LOGIN Feature", "Description", ["C1"])

    # When: Searching with lowercase
    result = task_list("test-epic", db_path=db_path, search="login")

    # Then: Should find the task
    assert len(result) == 1


def test_task_list_search_with_status_filter_combined(db_path, repo):
    """Test that search works with status filter."""
    from formaltask.cli.commands.task_list import task_list
    from formaltask.tasks.lifecycle import transition_task_status

    repo.create_epic("test-epic", "Test epic")
    # Login task - open
    repo.create_task("test-epic", "Implement login", "Login", ["C1"])
    # Login task - completed (must transition through in_progress first)
    completed_task_id = repo.create_task("test-epic", "Login tests", "Login tests", ["C1"])
    transition_task_status(db_path, completed_task_id, "in_progress")
    transition_task_status(db_path, completed_task_id, "completed")

    # When: Listing with both search and status filter
    result = task_list("test-epic", db_path=db_path, search="login", status="open")

    # Then: Should only return open tasks matching "login"
    assert len(result) == 1
    assert result[0]["status"] == "open"


def test_task_list_without_search_backward_compat(db_path, repo):
    """Test that task_list without search still works (backward compat)."""
    from formaltask.cli.commands.task_list import task_list

    repo.create_epic("test-epic", "Test epic")
    repo.create_task("test-epic", "Task 1", "Description", ["C1"])
    repo.create_task("test-epic", "Task 2", "Description", ["C1"])

    # When: Listing without search filter
    result = task_list("test-epic", db_path=db_path)

    # Then: Should return all tasks as list
    assert isinstance(result, list)
    assert len(result) == 2


def test_cli_task_list_search_flag(db_path, repo):
    """Test CLI with --search flag filters output."""
    import subprocess
    import sys

    repo.create_epic("test-epic", "Test epic")
    repo.create_task("test-epic", "Implement auth flow", "Description", ["C1"])
    repo.create_task("test-epic", "Add database", "Description", ["C1"])

    # When: Running CLI with --search flag
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "formaltask.cli.pm",
            "task", "list",
            "test-epic",
            "--search",
            "auth",
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
    )

    # Then: Should succeed and only show matching tasks
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "auth" in result.stdout.lower()
    assert "database" not in result.stdout.lower()
