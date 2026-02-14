"""Tests for _execute_ac_commands function (Task #2860).

Tests AC command execution with subprocess.run, timeout handling, and result formatting.
"""

import pytest


class TestExecuteAcCommandsPassing:
    """Test _execute_ac_commands with passing commands."""

    def test_passing_command_returns_in_passed_list(self):
        """_execute_ac_commands returns criterion id in passed list when command exits 0."""
        from formaltask.core.completion_state import _execute_ac_commands

        criteria = [{"id": "c-1", "text": "t", "command": "exit 0"}]
        result = _execute_ac_commands(criteria)

        assert result["passed"] == ["c-1"]
        assert result["failed"] == []

    def test_uses_text_as_fallback_id(self):
        """_execute_ac_commands uses text as fallback when id not present."""
        from formaltask.core.completion_state import _execute_ac_commands

        criteria = [{"text": "check something", "command": "exit 0"}]
        result = _execute_ac_commands(criteria)

        assert result["passed"] == ["check something"]
        assert result["failed"] == []

    def test_skips_criteria_without_command(self):
        """_execute_ac_commands skips criteria that have no command field."""
        from formaltask.core.completion_state import _execute_ac_commands

        criteria = [
            {"id": "c-1", "text": "manual check"},
            {"id": "c-2", "text": "auto check", "command": "exit 0"},
        ]
        result = _execute_ac_commands(criteria)

        # Only c-2 has a command, so only c-2 appears in results
        assert result["passed"] == ["c-2"]
        assert result["failed"] == []


class TestExecuteAcCommandsFailing:
    """Test _execute_ac_commands with failing commands."""

    def test_failing_command_returns_in_failed_list(self):
        """_execute_ac_commands returns criterion in failed list when command exits non-zero."""
        from formaltask.core.completion_state import _execute_ac_commands

        criteria = [{"id": "c-1", "text": "t", "command": "exit 1"}]
        result = _execute_ac_commands(criteria)

        assert result["passed"] == []
        assert len(result["failed"]) == 1
        failed = result["failed"][0]
        assert failed["criterion_id"] == "c-1"
        assert failed["command"] == "exit 1"
        assert failed["exit_code"] == 1

    def test_failed_includes_stderr(self):
        """_execute_ac_commands includes stderr in failed result."""
        from formaltask.core.completion_state import _execute_ac_commands

        criteria = [{"id": "c-1", "text": "t", "command": "echo 'error msg' >&2 && exit 1"}]
        result = _execute_ac_commands(criteria)

        assert len(result["failed"]) == 1
        assert "error msg" in result["failed"][0]["stderr"]


class TestExecuteAcCommandsTimeout:
    """Test _execute_ac_commands timeout handling."""

    def test_timeout_is_5_minutes(self, monkeypatch):
        """_execute_ac_commands uses 5 minute (300s) timeout."""
        import subprocess

        from formaltask.core.completion_state import _execute_ac_commands

        captured_timeout = None

        original_run = subprocess.run

        def mock_run(*args, **kwargs):
            nonlocal captured_timeout
            captured_timeout = kwargs.get("timeout")
            # Return success
            return original_run("exit 0", shell=True, capture_output=True, timeout=30)

        monkeypatch.setattr(subprocess, "run", mock_run)

        _execute_ac_commands([{"id": "c-1", "text": "t", "command": "exit 0"}])

        assert captured_timeout == 300

    def test_timeout_returns_as_failure(self, monkeypatch):
        """_execute_ac_commands treats timeout as failure with timeout flag."""
        import subprocess

        from formaltask.core.completion_state import _execute_ac_commands

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="sleep 1000", timeout=300)

        monkeypatch.setattr(subprocess, "run", mock_run)

        criteria = [{"id": "c-1", "text": "t", "command": "sleep 1000"}]
        result = _execute_ac_commands(criteria)

        assert result["passed"] == []
        assert len(result["failed"]) == 1
        failed = result["failed"][0]
        assert failed["criterion_id"] == "c-1"
        assert failed["timeout"] is True

    def test_oserror_returns_as_failure(self, monkeypatch):
        """_execute_ac_commands treats OSError as failure."""
        import subprocess

        from formaltask.core.completion_state import _execute_ac_commands

        def mock_run(*args, **kwargs):
            raise OSError("No such shell")

        monkeypatch.setattr(subprocess, "run", mock_run)

        criteria = [{"id": "c-1", "text": "t", "command": "some_command"}]
        result = _execute_ac_commands(criteria)

        assert result["passed"] == []
        assert len(result["failed"]) == 1
        failed = result["failed"][0]
        assert failed["criterion_id"] == "c-1"
        assert "OS error" in failed["stderr"]
