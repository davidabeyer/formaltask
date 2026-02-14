"""Tests for inlined restart logic in WorkerDashboard (Task #2680).

Tests double-tap restart confirmation inlined from RestartManager.
"""

import time
from unittest.mock import MagicMock, patch


class TestRestartInlineDoubleTapConfirmation:
    """Test double-tap confirmation behavior inlined in WorkerDashboard."""

    def test_restart_first_press_sets_pending_state(self) -> None:
        """First R press should set _pending_restart state."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        app = WorkerDashboard()
        # Set a selected task
        app.selected_task_id = 42

        # Mock notify to avoid widget issues
        app.notify = MagicMock()

        app.action_restart()

        # _pending_restart should be set to (task_id, timestamp)
        assert app._pending_restart is not None
        assert app._pending_restart[0] == 42

    def test_restart_first_press_shows_warning(self) -> None:
        """First R press should show warning notification."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        app = WorkerDashboard()
        app.selected_task_id = 42
        app.notify = MagicMock()

        app.action_restart()

        app.notify.assert_called_once()
        args, kwargs = app.notify.call_args
        assert "42" in args[0]
        assert kwargs.get("severity") == "warning"

    def test_restart_second_press_within_timeout_executes(self) -> None:
        """Second R press within 3s should execute restart."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        app = WorkerDashboard()
        app.selected_task_id = 42
        app.notify = MagicMock()
        # Set pending state
        app._pending_restart = (42, time.time())

        with patch.object(app, "_execute_restart") as mock_execute:
            app.action_restart()

        mock_execute.assert_called_once_with(42)
        # Pending should be cleared
        assert app._pending_restart is None

    def test_restart_second_press_after_timeout_resets_pending(self) -> None:
        """Second R press after 3s should reset pending state."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        app = WorkerDashboard()
        app.selected_task_id = 42
        app.notify = MagicMock()
        # Set pending state 4 seconds ago (expired)
        app._pending_restart = (42, time.time() - 4.0)

        app.action_restart()

        # Should have new pending state (not executed)
        assert app._pending_restart is not None
        assert app._pending_restart[0] == 42
        # Warning should be shown again
        app.notify.assert_called()
        args, kwargs = app.notify.call_args
        assert kwargs.get("severity") == "warning"

    def test_restart_different_task_resets_pending(self) -> None:
        """R press for different task should reset pending state."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        app = WorkerDashboard()
        app.selected_task_id = 99  # Different task
        app.notify = MagicMock()
        # Set pending for task 42
        app._pending_restart = (42, time.time())

        app.action_restart()

        # Should have new pending state for task 99
        assert app._pending_restart is not None
        assert app._pending_restart[0] == 99

    def test_restart_no_selection_shows_error(self) -> None:
        """R press with no selection should show error notification."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        app = WorkerDashboard()
        app.selected_task_id = None
        app.notify = MagicMock()

        app.action_restart()

        app.notify.assert_called_once()
        args, kwargs = app.notify.call_args
        assert "no worker" in args[0].lower()
        assert kwargs.get("severity") == "error"


class TestRestartInlineExecuteRestart:
    """Test _execute_restart method inlined in WorkerDashboard."""

    def test_execute_restart_validates_worktree_exists(self, tmp_path) -> None:
        """_execute_restart should validate worktree exists."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        app = WorkerDashboard()
        app.notify = MagicMock()
        app.clear_notifications = MagicMock()

        # Worktree doesn't exist - patch task_worktree to return nonexistent path
        with patch("formaltask.apps.dashboard.app.task_worktree") as mock_wt:
            mock_wt.return_value = tmp_path / ".claude" / "worktrees" / "task-42"
            app._execute_restart(42)

        # Should notify about missing worktree
        error_calls = [c for c in app.notify.call_args_list if c.kwargs.get("severity") == "error"]
        assert len(error_calls) >= 1
        assert any(
            "worktree" in str(c).lower() or "not found" in str(c).lower() for c in error_calls
        )

    def test_execute_restart_clears_notifications_first(self, tmp_path) -> None:
        """_execute_restart should clear notifications before starting."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        app = WorkerDashboard()
        app.notify = MagicMock()
        app.clear_notifications = MagicMock()

        # Create worktree
        worktree = tmp_path / ".claude" / "worktrees" / "task-42"
        worktree.mkdir(parents=True)

        with (
            patch("formaltask.apps.dashboard.app.Path") as mock_path,
            patch("formaltask.apps.dashboard.app.kill_session"),
            patch("formaltask.apps.dashboard.app.create_session", return_value=True),
            patch("subprocess.run") as mock_run,
            patch("formaltask.apps.dashboard.app.send_keys", return_value=True),
        ):
            mock_path.home.return_value = tmp_path
            mock_run.return_value = MagicMock(returncode=0)
            app._execute_restart(42)

        app.clear_notifications.assert_called_once()

    def test_execute_restart_notifies_on_success(self, tmp_path) -> None:
        """_execute_restart should notify with attach hint on success."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        app = WorkerDashboard()
        app.notify = MagicMock()
        app.clear_notifications = MagicMock()

        # Create worktree
        worktree = tmp_path / ".claude" / "worktrees" / "task-42"
        worktree.mkdir(parents=True)

        with (
            patch("formaltask.apps.dashboard.app.Path") as mock_path,
            patch("formaltask.apps.dashboard.app.kill_session"),
            patch("formaltask.apps.dashboard.app.create_session", return_value=True),
            patch("subprocess.run") as mock_run,
            patch("formaltask.apps.dashboard.app.send_keys", return_value=True),
        ):
            mock_path.home.return_value = tmp_path
            mock_run.return_value = MagicMock(returncode=0)
            app._execute_restart(42)

        # Should have success notification
        success_calls = [
            c
            for c in app.notify.call_args_list
            if "restarted" in str(c).lower() or c.kwargs.get("title") == "Restart Complete"
        ]
        assert len(success_calls) >= 1


class TestRestartInlineFailureModes:
    """Test _execute_restart error handling (P3 finding: subprocess failure modes)."""

    def test_execute_restart_handles_tmux_failure(self, tmp_path) -> None:
        """_execute_restart should handle tmux new-session failure."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        app = WorkerDashboard()
        app.notify = MagicMock()
        app.clear_notifications = MagicMock()

        # Create worktree
        worktree = tmp_path / ".claude" / "worktrees" / "task-42"
        worktree.mkdir(parents=True)

        with (
            patch("formaltask.apps.dashboard.app.Path") as mock_path,
            patch("formaltask.apps.dashboard.app.kill_session"),
            patch("subprocess.run") as mock_run,
        ):
            mock_path.home.return_value = tmp_path
            mock_run.return_value = MagicMock(returncode=1, stderr=b"error")
            app._execute_restart(42)

        error_calls = [c for c in app.notify.call_args_list if c.kwargs.get("severity") == "error"]
        assert len(error_calls) >= 1
        assert any("tmux" in str(c).lower() for c in error_calls)

    def test_execute_restart_handles_timeout(self, tmp_path) -> None:
        """_execute_restart should handle subprocess timeout."""
        import subprocess as sp

        from formaltask.apps.dashboard.app import WorkerDashboard

        app = WorkerDashboard()
        app.notify = MagicMock()
        app.clear_notifications = MagicMock()

        # Create worktree
        worktree = tmp_path / ".claude" / "worktrees" / "task-42"
        worktree.mkdir(parents=True)

        with (
            patch("formaltask.apps.dashboard.app.Path") as mock_path,
            patch("formaltask.apps.dashboard.app.kill_session"),
            patch("formaltask.apps.dashboard.app.create_session") as mock_create,
        ):
            mock_path.home.return_value = tmp_path
            mock_create.side_effect = sp.TimeoutExpired("tmux", 30)
            app._execute_restart(42)

        error_calls = [c for c in app.notify.call_args_list if c.kwargs.get("severity") == "error"]
        assert len(error_calls) >= 1
        assert any("timed out" in str(c).lower() for c in error_calls)

    def test_execute_restart_handles_oserror(self, tmp_path) -> None:
        """_execute_restart should handle OSError gracefully."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        app = WorkerDashboard()
        app.notify = MagicMock()
        app.clear_notifications = MagicMock()

        # Create worktree
        worktree = tmp_path / ".claude" / "worktrees" / "task-42"
        worktree.mkdir(parents=True)

        with (
            patch("formaltask.apps.dashboard.app.Path") as mock_path,
            patch("formaltask.apps.dashboard.app.kill_session"),
            patch("formaltask.apps.dashboard.app.create_session") as mock_create,
        ):
            mock_path.home.return_value = tmp_path
            mock_create.side_effect = OSError("Permission denied")
            app._execute_restart(42)

        error_calls = [c for c in app.notify.call_args_list if c.kwargs.get("severity") == "error"]
        assert len(error_calls) >= 1
        assert any("permission" in str(c).lower() for c in error_calls)

    def test_execute_restart_handles_send_keys_failure(self, tmp_path) -> None:
        """_execute_restart should handle send_keys failure."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        app = WorkerDashboard()
        app.notify = MagicMock()
        app.clear_notifications = MagicMock()

        # Create worktree
        worktree = tmp_path / ".claude" / "worktrees" / "task-42"
        worktree.mkdir(parents=True)

        with (
            patch("formaltask.apps.dashboard.app.Path") as mock_path,
            patch("formaltask.apps.dashboard.app.kill_session"),
            patch("formaltask.apps.dashboard.app.create_session", return_value=True),
            patch("subprocess.run") as mock_run,
            patch("formaltask.apps.dashboard.app.send_keys", return_value=False),
        ):
            mock_path.home.return_value = tmp_path
            mock_run.return_value = MagicMock(returncode=0)
            app._execute_restart(42)

        error_calls = [c for c in app.notify.call_args_list if c.kwargs.get("severity") == "error"]
        assert len(error_calls) >= 1
        assert any("send_keys" in str(c).lower() for c in error_calls)
