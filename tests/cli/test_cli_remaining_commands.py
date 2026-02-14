"""Tests for CLI remaining commands refactoring (Task #1382).

Updated for Task #2737: task_list() now returns list[dict] and raises ValueError.
These tests verify the new API and the execute() wrapper behavior.
"""

from argparse import Namespace

import pytest

from formaltask.cli.base import CLIError
from formaltask.cli.exit_codes import ExitCode


class TestTaskListReturnTypes:
    """Tests for task_list return type consistency."""

    def test_task_list_returns_list_on_success(self, db_path, repo):
        """task_list returns list[dict] on success."""
        from formaltask.cli.commands.task_list import task_list

        repo.create_epic("test-epic", "Test epic")
        repo.create_task("test-epic", "Task 1", "Description", ["Criterion"])

        result = task_list("test-epic", db_path=db_path)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == "Task 1"

    def test_task_list_raises_valueerror_on_epic_not_found(self, db_path):
        """task_list raises ValueError on missing epic."""
        from formaltask.cli.commands.task_list import task_list

        with pytest.raises(ValueError, match="not found"):
            task_list("nonexistent", db_path=db_path)

    def test_task_list_returns_empty_list_on_no_tasks(self, db_path, repo):
        """task_list returns empty list when epic has no tasks."""
        from formaltask.cli.commands.task_list import task_list

        repo.create_epic("empty-epic", "Epic with no tasks")

        result = task_list("empty-epic", db_path=db_path)

        assert isinstance(result, list)
        assert result == []


class TestTaskListExecuteErrorPaths:
    """Tests for task_list execute() wrapper error handling."""

    def test_execute_epic_not_found_raises_cli_error_in_json_mode(self, db_path, monkeypatch):
        """execute() raises CLIError with NOT_FOUND for missing epic in JSON mode."""
        from formaltask.cli.commands import task_list as task_list_module

        args = Namespace(
            epic_name="nonexistent-epic",
            status=None,
            search=None,
            json=True,
            stream=False,
            db_path=db_path,
        )

        with pytest.raises(CLIError) as exc_info:
            task_list_module.execute.__wrapped__(db_path, args)

        assert exc_info.value.exit_code == ExitCode.NOT_FOUND
        assert "nonexistent-epic" in exc_info.value.message

    def test_execute_epic_not_found_returns_1_in_human_mode(self, db_path, capsys):
        """execute() returns 1 and prints error for missing epic in human mode."""
        from formaltask.cli.commands import task_list as task_list_module

        args = Namespace(
            epic_name="nonexistent-epic", status=None, search=None, json=False, db_path=db_path
        )

        result = task_list_module.execute.__wrapped__(db_path, args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.out
        assert "not found" in captured.out.lower()

    def test_execute_no_tasks_returns_zero_in_human_mode(self, db_path, repo, capsys, monkeypatch):
        """execute() returns 0 when epic has no tasks (human mode)."""
        from formaltask.cli.commands import task_list as task_list_module

        repo.create_epic("empty-epic", "An epic with no tasks")

        args = Namespace(
            epic_name="empty-epic", status=None, search=None, json=False, db_path=db_path
        )

        result = task_list_module.execute.__wrapped__(db_path, args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No tasks found" in captured.out


# Note: TestReviewStatusJsonErrorPaths and TestReviewSkipJsonErrorPaths removed
# in Task #2323 - deprecated command files deleted
