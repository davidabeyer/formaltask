"""Tests for dashboard formatters."""

from __future__ import annotations

from rich.text import Text


class TestFormatSelectedWorkerTerminal:
    """Tests for format_selected_worker_terminal formatter."""

    def test_format_selected_worker_terminal_none_returns_select_prompt(self) -> None:
        """format_selected_worker_terminal(None) returns 'Select a worker' Text."""
        from formaltask.apps.dashboard.formatters import format_selected_worker_terminal

        result = format_selected_worker_terminal(None)
        assert isinstance(result, Text)
        assert "Select a worker to view terminal" in str(result)

    def test_format_selected_worker_terminal_with_task_id(self) -> None:
        """format_selected_worker_terminal shows captured output for task."""
        from formaltask.apps.dashboard.formatters import format_selected_worker_terminal

        result = format_selected_worker_terminal(42, captured_content="Worker output")
        text = str(result)
        assert "Worker output" in text

    def test_format_selected_worker_terminal_with_blocked_count(self) -> None:
        """format_selected_worker_terminal shows inbox hint when blocked."""
        from formaltask.apps.dashboard.formatters import format_selected_worker_terminal

        result = format_selected_worker_terminal(42, blocked_count=2, captured_content="Worker output")
        text = str(result)
        assert "2 blocked" in text
        assert "press i for inbox" in text


class TestGetSidebarStatusStaleWorkers:
    """Tests for get_sidebar_status with stale workers (Task #2810).

    Workers with active tmux sessions should appear in RUNNING section
    regardless of is_stale value.
    """

    def test_get_sidebar_status_stale_with_tmux_returns_running(self) -> None:
        """Stale worker with active tmux session should return 'running'."""
        from formaltask.apps.dashboard.formatters import get_sidebar_status

        # Stale worker with active tmux session should be "running"
        result = get_sidebar_status(
            health_state="implementing",
            tmux_exists=True,
        )
        assert result == "running", "Stale worker with tmux_exists=True should return 'running'"

    def test_get_sidebar_status_non_stale_with_tmux_returns_running(self) -> None:
        """Non-stale worker with active tmux session should return 'running'."""
        from formaltask.apps.dashboard.formatters import get_sidebar_status

        result = get_sidebar_status(
            health_state="implementing",
            tmux_exists=True,
        )
        assert result == "running", "Non-stale worker with tmux_exists=True should return 'running'"

    def test_get_sidebar_status_stale_no_tmux_returns_idle(self) -> None:
        """Stale worker without tmux session should return 'idle'."""
        from formaltask.apps.dashboard.formatters import get_sidebar_status

        result = get_sidebar_status(
            health_state="implementing",
            tmux_exists=False,
        )
        assert result == "idle", "Worker without tmux_exists should return 'idle'"

    def test_get_sidebar_status_blocked_takes_precedence(self) -> None:
        """Blocked state should return 'error' regardless of tmux."""
        from formaltask.apps.dashboard.formatters import get_sidebar_status

        result = get_sidebar_status(
            health_state="blocked",
            tmux_exists=True,
        )
        assert result == "error", "Blocked state should return 'error' regardless of tmux"

    def test_get_sidebar_status_done_with_tmux_returns_idle(self) -> None:
        """Done/completed with active tmux should still return 'idle'."""
        from formaltask.apps.dashboard.formatters import get_sidebar_status

        # Test each IDLE_STATE with tmux_exists=True
        for health_state in ("done", "completed", "exited", "awaiting_merge"):
            result = get_sidebar_status(
                health_state=health_state,
                tmux_exists=True,
            )
            assert result == "idle", f"{health_state} with tmux_exists=True should return 'idle'"

