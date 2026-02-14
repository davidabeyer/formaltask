"""Tests for session_utils module.

Task #1984: Extracted from stop_handoff_enforcer.py and stop_workflow_enforcer.py
to eliminate code duplication.
"""

from __future__ import annotations


def test_get_task_id_from_env_variable(monkeypatch) -> None:
    """Should detect task ID from TASK_ID environment variable."""
    from formaltask.workers.context import get_task_id_from_session

    monkeypatch.setenv("TASK_ID", "42")
    monkeypatch.delenv("TMUX", raising=False)

    result = get_task_id_from_session()
    assert result == 42


def test_get_task_id_from_env_invalid_value(monkeypatch) -> None:
    """Should return None for invalid TASK_ID value."""
    from unittest.mock import patch

    from formaltask.workers.context import get_task_id_from_session

    monkeypatch.setenv("TASK_ID", "not-a-number")
    monkeypatch.delenv("TMUX", raising=False)
    with patch("formaltask.workers.context.os.getcwd", return_value="/tmp"):
        result = get_task_id_from_session()
    assert result is None


def test_task_id_env_takes_precedence_over_tmux(monkeypatch) -> None:
    """TASK_ID env var should take precedence over TMUX session detection."""
    from unittest.mock import MagicMock, patch

    from formaltask.workers.context import get_task_id_from_session

    # Set both TASK_ID and TMUX
    monkeypatch.setenv("TASK_ID", "100")
    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,12345,0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "task-200\n"  # TMUX says 200

    with patch("formaltask.workers.context.subprocess.run", return_value=mock_result):
        result = get_task_id_from_session()

    assert result == 100  # TASK_ID wins


def test_task_id_env_takes_precedence_over_worktree(monkeypatch) -> None:
    """TASK_ID env var should take precedence over worktree path detection."""
    from unittest.mock import patch

    from formaltask.workers.context import get_task_id_from_session

    monkeypatch.setenv("TASK_ID", "100")
    monkeypatch.delenv("TMUX", raising=False)

    with patch(
        "formaltask.workers.context.os.getcwd",
        return_value="/Users/test/.claude/worktrees/task-200",
    ):
        result = get_task_id_from_session()

    assert result == 100  # TASK_ID wins


def test_get_task_id_from_session_returns_none_when_not_in_tmux_or_worktree(monkeypatch) -> None:
    """Should return None when not in TMUX and not in a worktree."""
    from unittest.mock import patch

    from formaltask.workers.context import get_task_id_from_session

    monkeypatch.delenv("TMUX", raising=False)
    # Mock cwd to be outside any worktree
    with patch("formaltask.workers.context.os.getcwd", return_value="/tmp"):
        result = get_task_id_from_session()
    assert result is None


def test_get_task_id_from_worktree_path(monkeypatch) -> None:
    """Should detect task ID from worktree directory path when TMUX not set."""
    from unittest.mock import patch

    from formaltask.workers.context import get_task_id_from_session

    monkeypatch.delenv("TMUX", raising=False)
    # Mock cwd to be in a task worktree
    with patch(
        "formaltask.workers.context.os.getcwd",
        return_value="/Users/test/.claude/worktrees/task-1234",
    ):
        result = get_task_id_from_session()
    assert result == 1234


def test_get_task_id_from_worktree_nested_path(monkeypatch) -> None:
    """Should detect task ID when in a subdirectory of worktree."""
    from unittest.mock import patch

    from formaltask.workers.context import get_task_id_from_session

    monkeypatch.delenv("TMUX", raising=False)
    with patch(
        "formaltask.workers.context.os.getcwd",
        return_value="/Users/test/.claude/worktrees/task-5678/src/hooks",
    ):
        result = get_task_id_from_session()
    assert result == 5678


def test_tmux_takes_precedence_over_worktree(monkeypatch) -> None:
    """TMUX session detection should take precedence over worktree path."""
    from unittest.mock import MagicMock, patch

    from formaltask.workers.context import get_task_id_from_session

    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,12345,0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "task-100\n"

    # Even though we're in task-200 worktree, TMUX says task-100
    with (
        patch("formaltask.workers.context.subprocess.run", return_value=mock_result),
        patch(
            "formaltask.workers.context.os.getcwd",
            return_value="/Users/test/.claude/worktrees/task-200",
        ),
    ):
        result = get_task_id_from_session()

    assert result == 100  # TMUX wins


def test_get_task_id_from_session_returns_id_for_valid_session(monkeypatch) -> None:
    """Should return task ID for task-{id} session name."""
    from unittest.mock import MagicMock, patch

    from formaltask.workers.context import get_task_id_from_session

    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,12345,0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "task-42\n"

    with patch("formaltask.workers.context.subprocess.run", return_value=mock_result):
        result = get_task_id_from_session()

    assert result == 42


def test_get_task_id_from_session_returns_none_for_non_task_session(monkeypatch) -> None:
    """Should return None for non-task session names."""
    from unittest.mock import MagicMock, patch

    from formaltask.workers.context import get_task_id_from_session

    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,12345,0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "main-session\n"

    with (
        patch("formaltask.workers.context.subprocess.run", return_value=mock_result),
        patch("formaltask.workers.context.os.getcwd", return_value="/tmp/not-a-task"),
    ):
        result = get_task_id_from_session()

    assert result is None


def test_get_task_id_from_session_returns_none_on_subprocess_failure(monkeypatch) -> None:
    """Should return None when tmux command fails."""
    from unittest.mock import MagicMock, patch

    from formaltask.workers.context import get_task_id_from_session

    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,12345,0")

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""

    with (
        patch("formaltask.workers.context.subprocess.run", return_value=mock_result),
        patch("formaltask.workers.context.os.getcwd", return_value="/tmp/not-a-task"),
    ):
        result = get_task_id_from_session()

    assert result is None


# =============================================================================
# Git Sibling Worktree Pattern Tests
# =============================================================================


def test_get_task_id_from_git_sibling_worktree(monkeypatch) -> None:
    """Should detect task ID from git sibling worktree pattern (task-{id}-{branch})."""
    from unittest.mock import patch

    from formaltask.workers.context import get_task_id_from_session

    monkeypatch.delenv("TASK_ID", raising=False)
    monkeypatch.delenv("TMUX", raising=False)

    # Git sibling worktree pattern: task-{id}-{branch-name}
    with patch(
        "formaltask.workers.context.os.getcwd",
        return_value="/Users/test/projects/task-1234-feature-branch",
    ):
        result = get_task_id_from_session()
    assert result == 1234


def test_get_task_id_from_git_sibling_worktree_nested(monkeypatch) -> None:
    """Should detect task ID from nested path in git sibling worktree."""
    from unittest.mock import patch

    from formaltask.workers.context import get_task_id_from_session

    monkeypatch.delenv("TASK_ID", raising=False)
    monkeypatch.delenv("TMUX", raising=False)

    # Nested path in git sibling worktree
    with patch(
        "formaltask.workers.context.os.getcwd",
        return_value="/Users/test/projects/task-999-my-feature/src/lib",
    ):
        result = get_task_id_from_session()
    assert result == 999


def test_rejects_ambiguous_task_path(monkeypatch) -> None:
    """Should NOT detect task ID from ambiguous paths like /tmp/task-123/."""
    from unittest.mock import patch

    from formaltask.workers.context import get_task_id_from_session

    monkeypatch.delenv("TASK_ID", raising=False)
    monkeypatch.delenv("TMUX", raising=False)

    # This path matches neither .claude/worktrees nor task-{id}-{branch} pattern
    with patch(
        "formaltask.workers.context.os.getcwd",
        return_value="/tmp/task-123",
    ):
        result = get_task_id_from_session()
    assert result is None


def test_rejects_random_directory_with_task_in_name(monkeypatch) -> None:
    """Should NOT detect task ID from random directories containing 'task-'."""
    from unittest.mock import patch

    from formaltask.workers.context import get_task_id_from_session

    monkeypatch.delenv("TASK_ID", raising=False)
    monkeypatch.delenv("TMUX", raising=False)

    # Random directory - should NOT match
    with patch(
        "formaltask.workers.context.os.getcwd",
        return_value="/home/user/task-456/project",
    ):
        result = get_task_id_from_session()
    assert result is None


# =============================================================================
# Mismatch Warning Tests
# =============================================================================


def test_logs_warning_on_task_id_mismatch(monkeypatch, caplog) -> None:
    """Should log warning when TASK_ID env and TMUX session name disagree."""
    import logging
    from unittest.mock import MagicMock, patch

    from formaltask.workers.context import get_task_id_from_session

    # Set up logging capture
    caplog.set_level(logging.WARNING)

    # TASK_ID says 100, TMUX says 200
    monkeypatch.setenv("TASK_ID", "100")
    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,12345,0")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "task-200\n"

    with patch("formaltask.workers.context.subprocess.run", return_value=mock_result):
        result = get_task_id_from_session()

    # Should still return TASK_ID (priority)
    assert result == 100

    # Should have logged a warning about the mismatch
    assert "TASK_ID mismatch" in caplog.text
    assert "env=100" in caplog.text
    assert "tmux_session=200" in caplog.text
