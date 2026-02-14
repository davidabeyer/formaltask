"""Tests for selected worker terminal formatter.

TDD tests for:
- format_selected_worker_terminal with task_id and captured content
- format_selected_worker_terminal with None (no selection)
- format_selected_worker_terminal with blocked count hint
"""

from __future__ import annotations

from rich.text import Text


class TestFormatSelectedWorkerTerminal:
    """Tests for format_selected_worker_terminal formatter."""

    def test_format_selected_worker_terminal_none_shows_select_prompt(self) -> None:
        """format_selected_worker_terminal(None) shows 'Select a worker' text."""
        from formaltask.apps.dashboard.formatters import format_selected_worker_terminal

        result = format_selected_worker_terminal(None)
        assert isinstance(result, Text)
        assert "Select a worker to view terminal" in str(result)

    def test_format_selected_worker_terminal_with_task_id_shows_output(self) -> None:
        """format_selected_worker_terminal shows captured output for selected task."""
        from formaltask.apps.dashboard.formatters import format_selected_worker_terminal

        captured = "Worker output line 1\nWorker output line 2"
        result = format_selected_worker_terminal(42, captured_content=captured)
        text = str(result)
        assert "Worker output line 1" in text
        assert "Worker output line 2" in text

    def test_format_selected_worker_terminal_empty_output_shows_placeholder(self) -> None:
        """format_selected_worker_terminal shows placeholder when no output captured."""
        from formaltask.apps.dashboard.formatters import format_selected_worker_terminal

        result = format_selected_worker_terminal(99, captured_content=None)
        assert "No output captured" in str(result)

    def test_format_selected_worker_terminal_with_blocked_count_shows_hint(self) -> None:
        """format_selected_worker_terminal shows inbox hint when blocked_count > 0."""
        from formaltask.apps.dashboard.formatters import format_selected_worker_terminal

        result = format_selected_worker_terminal(42, blocked_count=3, captured_content="Some output")
        text = str(result)
        assert "3 blocked" in text
        assert "press i for inbox" in text

    def test_format_selected_worker_terminal_zero_blocked_no_hint(self) -> None:
        """format_selected_worker_terminal shows no hint when blocked_count is 0."""
        from formaltask.apps.dashboard.formatters import format_selected_worker_terminal

        result = format_selected_worker_terminal(42, blocked_count=0, captured_content="Some output")
        text = str(result)
        assert "blocked" not in text
        assert "press i" not in text
