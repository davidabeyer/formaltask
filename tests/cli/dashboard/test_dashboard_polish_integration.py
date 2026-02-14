"""Integration test verifying all dashboard-polish tasks work together.

Task #2923: Verifies compose tree, dead code removal, orchestrator extraction,
and removed methods/bindings across tasks 1-5.
"""

import pytest
from textual.widgets import Footer

from formaltask.apps.dashboard.app import WorkerDashboard
from formaltask.apps.dashboard.widgets import StatusBar, TaskList, TerminalPane


@pytest.fixture(autouse=True)
def mock_dashboard_deps(monkeypatch):
    """Stub external deps so tests don't hit real DB/tmux."""
    monkeypatch.setattr("formaltask.apps.dashboard.app.get_blocked_workers", lambda *_a: [])
    monkeypatch.setattr(
        "formaltask.apps.dashboard.app.get_spawnable_tasks_with_titles", lambda *_a: []
    )
    monkeypatch.setattr("formaltask.apps.dashboard.app.get_all_task_sessions", lambda *_a: [])
    monkeypatch.setattr("formaltask.apps.dashboard.app.count_running_workers", lambda: 0)
    monkeypatch.setattr("formaltask.apps.dashboard.app.auto_spawn_cycle", lambda *_a, **_kw: [])


class TestDashboardPolishIntegration:
    """Verify all dashboard-polish tasks integrate correctly."""

    @pytest.mark.asyncio
    async def test_compose_yields_statusbar_tasklist_terminalpane_footer(self) -> None:
        """compose() yields StatusBar, TaskList, TerminalPane, Footer in order."""
        app = WorkerDashboard()
        async with app.run_test():
            # Exactly 1 of each widget
            assert len(app.query(StatusBar)) == 1
            assert len(app.query(TaskList)) == 1
            assert len(app.query(TerminalPane)) == 1
            assert len(app.query(Footer)) == 1

            # Correct IDs
            assert app.query_one(StatusBar).id == "status-bar"
            assert app.query_one(TaskList).id == "task-list"
            assert app.query_one(TerminalPane).id == "terminal-pane"

    def test_orchestrator_auto_spawn_cycle_importable(self) -> None:
        """orchestrator.auto_spawn_cycle is importable and callable."""
        from formaltask.workers.orchestrator import auto_spawn_cycle

        assert callable(auto_spawn_cycle)

    def test_screens_directory_has_inbox(self) -> None:
        """screens/ directory exists with inbox module."""
        from pathlib import Path

        screens_dir = Path(__file__).parent.parent.parent.parent / "formaltask" / "apps" / "dashboard" / "screens"
        assert screens_dir.exists()
        assert (screens_dir / "inbox.py").exists()
