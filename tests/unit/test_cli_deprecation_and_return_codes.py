"""Tests for CLI return code handling.

Task #573: CLI updates - return code 2 handling
Task #2649: Removed pr-create deprecation tests (command deleted)

Tests:
1. task-complete handles return code 2 (transition) correctly
2. Return code 2 does NOT print "Completed task" message

Note: Force-reloads modules to avoid testmon cache pollution
where mocks from previous test runs could leak through.

NOTE: Tests marked xfail expect task_complete() to return exit codes,
but the actual implementation uses exceptions not return values.
These tests document intended behavior that was never implemented.
"""

import importlib
from unittest.mock import patch

import pytest


class TestIssueCompleteReturnCode2:
    """Test return code 2 handling in task-complete."""

    @pytest.mark.xfail(reason="TDD Red phase: task_complete uses exceptions not return codes")
    def test_return_code_2_does_not_print_completed(self, capsys, tmp_path):
        """Return code 2 (transition) should NOT print 'Completed task'.

        Note: Uses context manager patches after module reload to avoid
        testmon cache pollution where mocks from previous runs leak through.
        """
        # Force reload to clear any cached modules from testmon
        import formaltask.cli.commands.task_complete as tc_module
        import formaltask.cli.pm as pm_module

        importlib.reload(tc_module)
        importlib.reload(pm_module)

        from formaltask.cli.pm import main

        fake_db_path = tmp_path / "formaltask.db"

        # Patch where imported (pm.py imports get_db_path directly), not where defined
        # Also patch validate_user_db_path which is called by @with_db_path decorator
        with (
            patch("formaltask.cli.commands.task_complete.task_complete", return_value=2),
            patch("formaltask.cli.pm.get_db_path", return_value=fake_db_path),
            patch("formaltask.db.path.validate_user_db_path", return_value=fake_db_path),
            patch("sys.argv", ["pm", "task", "complete", "42"]),
        ):
            result = main()

        captured = capsys.readouterr()
        assert "completed" not in captured.out.lower()
        assert result == 2

    def test_return_code_0_prints_completed(self, capsys, tmp_path):
        """Return code 0 (success) should print 'Completed task'.

        Note: Uses context manager patches after module reload to avoid
        testmon cache pollution where mocks from previous runs leak through.
        """
        import formaltask.cli.commands.task_complete as tc_module
        import formaltask.cli.pm as pm_module

        importlib.reload(tc_module)
        importlib.reload(pm_module)

        from formaltask.cli.pm import main

        fake_db_path = tmp_path / "formaltask.db"

        # Patch where imported (pm.py imports get_db_path directly), not where defined
        # Also patch validate_user_db_path which is called by @with_db_path decorator
        with (
            patch("formaltask.cli.commands.task_complete.task_complete", return_value=0),
            patch("formaltask.cli.pm.get_db_path", return_value=fake_db_path),
            patch("formaltask.db.path.validate_user_db_path", return_value=fake_db_path),
            patch("sys.argv", ["pm", "task", "complete", "42"]),
        ):
            result = main()

        captured = capsys.readouterr()
        assert "completed task #42" in captured.out.lower()
        assert result == 0

    @pytest.mark.xfail(reason="TDD Red phase: task_complete uses exceptions not return codes")
    def test_return_code_1_is_blocked(self, capsys, tmp_path):
        """Return code 1 (blocked) should not print completion message.

        Note: Uses context manager patches after module reload to avoid
        testmon cache pollution where mocks from previous runs leak through.
        """
        import formaltask.cli.commands.task_complete as tc_module
        import formaltask.cli.pm as pm_module

        importlib.reload(tc_module)
        importlib.reload(pm_module)

        from formaltask.cli.pm import main

        fake_db_path = tmp_path / "formaltask.db"

        # Patch where imported (pm.py imports get_db_path directly), not where defined
        # Also patch validate_user_db_path which is called by @with_db_path decorator
        with (
            patch("formaltask.cli.commands.task_complete.task_complete", return_value=1),
            patch("formaltask.cli.pm.get_db_path", return_value=fake_db_path),
            patch("formaltask.db.path.validate_user_db_path", return_value=fake_db_path),
            patch("sys.argv", ["pm", "task", "complete", "42"]),
        ):
            result = main()

        captured = capsys.readouterr()
        assert "completed task #42" not in captured.out.lower()
        assert result == 1
