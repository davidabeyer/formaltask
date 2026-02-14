"""Tests for tmux.create_session() function."""

import subprocess
from unittest.mock import MagicMock

import pytest

from formaltask import tmux


class TestCreateSession:
    """Tests for create_session() function."""

    def test_create_session_basic_success(self, monkeypatch):
        """create_session creates a detached tmux session and returns True."""
        mock_run = MagicMock(return_value=subprocess.CompletedProcess(args=["tmux", "-V"], returncode=0, stdout="tmux 3.4\n"))
        monkeypatch.setattr(subprocess, "run", mock_run)

        result = tmux.create_session("task-42", "/path/to/worktree")

        assert result is True
        # Verify tmux new-session was called
        calls = mock_run.call_args_list
        assert any("new-session" in str(c) for c in calls)

    def test_create_session_with_env_vars_tmux_3_2_plus(self, monkeypatch):
        """create_session uses -e flag for env vars on tmux 3.2+."""
        mock_run = MagicMock(return_value=subprocess.CompletedProcess(args=["tmux", "-V"], returncode=0, stdout="tmux 3.4\n"))
        monkeypatch.setattr(subprocess, "run", mock_run)

        result = tmux.create_session(
            "task-42", "/path/to/worktree", env_vars={"PROJECT_ROOT": "/main/repo"}
        )

        assert result is True
        # Find the new-session call and check for -e flag
        for c in mock_run.call_args_list:
            args = c[0][0] if c[0] else c[1].get("args", [])
            if "new-session" in args:
                assert "-e" in args
                assert "PROJECT_ROOT=/main/repo" in args
                break
        else:
            pytest.fail("new-session not called with -e flag")

    def test_create_session_with_env_vars_tmux_pre_3_2_uses_set_environment(self, monkeypatch):
        """create_session uses set-environment fallback for tmux < 3.2."""
        calls_made = []

        def mock_run(cmd, **_kwargs):
            calls_made.append(cmd)
            # First call: version check
            if "-V" in cmd:
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="tmux 3.1c\n")
            # Second call: new-session or set-environment
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = tmux.create_session(
            "task-42", "/path/to/worktree", env_vars={"PROJECT_ROOT": "/main/repo"}
        )

        assert result is True
        # Verify set-environment was called with correct args
        set_env_calls = [c for c in calls_made if "set-environment" in c]
        assert len(set_env_calls) == 1
        set_env_cmd = set_env_calls[0]
        assert "PROJECT_ROOT" in set_env_cmd
        assert "/main/repo" in set_env_cmd

    def test_create_session_returns_false_on_subprocess_failure(self, monkeypatch):
        """create_session returns False when tmux command fails."""
        mock_run = MagicMock(return_value=subprocess.CompletedProcess(args=["tmux"], returncode=1))
        monkeypatch.setattr(subprocess, "run", mock_run)

        result = tmux.create_session("task-42", "/path/to/worktree")

        assert result is False

    def test_create_session_returns_false_on_timeout(self, monkeypatch):
        """create_session returns False on subprocess timeout."""
        mock_run = MagicMock(side_effect=subprocess.TimeoutExpired(cmd="tmux", timeout=30))
        monkeypatch.setattr(subprocess, "run", mock_run)

        result = tmux.create_session("task-42", "/path/to/worktree")

        assert result is False

    def test_create_session_returns_false_when_tmux_not_found(self, monkeypatch):
        """create_session returns False when tmux binary not found."""
        mock_run = MagicMock(side_effect=FileNotFoundError("tmux not found"))
        monkeypatch.setattr(subprocess, "run", mock_run)

        result = tmux.create_session("task-42", "/path/to/worktree")

        assert result is False

    def test_create_session_returns_false_on_oserror(self, monkeypatch):
        """create_session returns False on general OSError."""
        mock_run = MagicMock(side_effect=OSError("Permission denied"))
        monkeypatch.setattr(subprocess, "run", mock_run)

        result = tmux.create_session("task-42", "/path/to/worktree")

        assert result is False


class TestGetTmuxVersion:
    """Tests for get_tmux_version() function (moved from spawner.py)."""

    def test_get_tmux_version_parses_version_string(self, monkeypatch):
        """get_tmux_version returns (major, minor) tuple."""
        mock_run = MagicMock(return_value=subprocess.CompletedProcess(args=["tmux", "-V"], returncode=0, stdout="tmux 3.4\n"))
        monkeypatch.setattr(subprocess, "run", mock_run)

        result = tmux.get_tmux_version()

        assert result == (3, 4)

    def test_get_tmux_version_handles_letter_suffix(self, monkeypatch):
        """get_tmux_version handles versions like '3.1c'."""
        mock_run = MagicMock(return_value=subprocess.CompletedProcess(args=["tmux", "-V"], returncode=0, stdout="tmux 3.1c\n"))
        monkeypatch.setattr(subprocess, "run", mock_run)

        result = tmux.get_tmux_version()

        assert result == (3, 1)

    def test_get_tmux_version_returns_0_0_on_failure(self, monkeypatch):
        """get_tmux_version returns (0, 0) when detection fails."""
        mock_run = MagicMock(return_value=subprocess.CompletedProcess(args=["tmux", "-V"], returncode=1))
        monkeypatch.setattr(subprocess, "run", mock_run)

        result = tmux.get_tmux_version()

        assert result == (0, 0)

    def test_get_tmux_version_returns_0_0_on_timeout(self, monkeypatch):
        """get_tmux_version returns (0, 0) on timeout."""
        mock_run = MagicMock(side_effect=subprocess.TimeoutExpired(cmd="tmux", timeout=5))
        monkeypatch.setattr(subprocess, "run", mock_run)

        result = tmux.get_tmux_version()

        assert result == (0, 0)
