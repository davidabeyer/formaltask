"""Tests for TerminalPane widget (Task #2920)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from rich.text import Text


@pytest.fixture(autouse=True)
def mock_dashboard_queries(monkeypatch):
    """Stub out DB queries so Textual app starts without a real database."""
    monkeypatch.setattr("formaltask.apps.dashboard.app.get_blocked_workers", lambda *a: [])
    monkeypatch.setattr(
        "formaltask.apps.dashboard.app.get_spawnable_tasks_with_titles", lambda *a: []
    )
    monkeypatch.setattr("formaltask.apps.dashboard.app.get_all_task_sessions", lambda *a: [])
    monkeypatch.setattr("formaltask.apps.dashboard.app.count_running_workers", lambda: 0)
    monkeypatch.setattr("formaltask.apps.dashboard.app.auto_spawn_cycle", lambda *a, **kw: [])


class TestTerminalPaneRendering:
    """Tests for TerminalPane content rendering."""

    def test_terminal_pane_shows_placeholder_when_no_selection(self) -> None:
        """TerminalPane with no task_id shows placeholder text."""
        from formaltask.apps.dashboard.widgets import TerminalPane

        pane = TerminalPane(id="terminal-pane")
        assert pane._task_id is None

        result = pane.render_content()
        assert "Select a worker" in result.plain

    def test_terminal_pane_render_content_with_data(self) -> None:
        """TerminalPane.render_content() uses format_selected_worker_terminal."""
        from formaltask.apps.dashboard.widgets import TerminalPane

        pane = TerminalPane(id="terminal-pane")
        pane._task_id = 42
        pane._captured_content = "some output"
        pane._blocked_count = 1

        with patch(
            "formaltask.apps.dashboard.widgets.terminal_pane.format_selected_worker_terminal"
        ) as mock_fmt:
            mock_fmt.return_value = Text("formatted output")
            result = pane.render_content()
            mock_fmt.assert_called_once_with(42, blocked_count=1, captured_content="some output")
            assert "formatted output" in result.plain


class TestComposeIncludesTerminalPane:
    """Tests for compose() including TerminalPane."""

    @pytest.mark.asyncio
    async def test_compose_includes_terminal_pane(self) -> None:
        """compose() yields a TerminalPane with id='terminal-pane'."""
        from formaltask.apps.dashboard.app import WorkerDashboard
        from formaltask.apps.dashboard.widgets import TerminalPane

        app = WorkerDashboard()
        async with app.run_test():
            panes = app.query(TerminalPane)
            assert len(panes) == 1, f"Expected 1 TerminalPane, got {len(panes)}"
            assert panes.first().id == "terminal-pane"


class TestTerminalPaneIntegration:
    """Integration tests for terminal pane updates."""

    @pytest.mark.asyncio
    async def test_terminal_updates_on_worker_states_updated(self) -> None:
        """on_worker_states_updated passes captured_terminal_content to TerminalPane."""
        from formaltask.apps.dashboard.app import WorkerDashboard, WorkerStatesUpdated
        from formaltask.apps.dashboard.widgets import TerminalPane

        app = WorkerDashboard()
        async with app.run_test() as pilot:
            app.post_message(
                WorkerStatesUpdated(
                    states={},
                    spawnable_tasks=[],
                    blocked_workers=[],
                    captured_terminal_content="terminal output here",
                )
            )
            await pilot.pause()

            pane = app.query_one("#terminal-pane", TerminalPane)
            assert pane._captured_content == "terminal output here"
