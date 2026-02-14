"""Tests for dashboard app.py module."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_dashboard_queries(monkeypatch):
    """Stub out DB queries so Textual app starts without a real database."""
    monkeypatch.setattr("formaltask.apps.dashboard.app.get_blocked_workers", lambda *a: [])
    monkeypatch.setattr("formaltask.apps.dashboard.app.get_spawnable_tasks_with_titles", lambda *a: [])
    monkeypatch.setattr("formaltask.apps.dashboard.app.get_all_task_sessions", lambda *a: [])
    monkeypatch.setattr("formaltask.apps.dashboard.app.count_running_workers", lambda: 0)
    monkeypatch.setattr("formaltask.apps.dashboard.app.auto_spawn_cycle", lambda *a, **kw: [])


# --- Task #2908: App rewrite tests ---


class TestComposeLayout:
    """Tests for flat compose() layout (Task #2908)."""

    @pytest.mark.asyncio
    async def test_compose_flat_layout(self) -> None:
        """compose() yields exactly StatusBar, TaskList, Footer."""
        from textual.containers import Horizontal
        from textual.widgets import Footer

        from formaltask.apps.dashboard.app import WorkerDashboard
        from formaltask.apps.dashboard.widgets import StatusBar, TaskList

        app = WorkerDashboard()
        async with app.run_test():
            # StatusBar must exist
            status_bars = app.query(StatusBar)
            assert len(status_bars) == 1, f"Expected 1 StatusBar, got {len(status_bars)}"

            # TaskList must exist with id='task-list'
            task_lists = app.query(TaskList)
            assert len(task_lists) == 1, f"Expected 1 TaskList, got {len(task_lists)}"
            assert task_lists.first().id == "task-list"

            # Footer must exist
            footers = app.query(Footer)
            assert len(footers) == 1, f"Expected 1 Footer, got {len(footers)}"

            # No Horizontal containers
            horizontals = app.query(Horizontal)
            assert len(horizontals) == 0, f"Expected 0 Horizontal, got {len(horizontals)}"

            # No Static with id='detail' or id='workers'
            for widget_id in ("detail", "workers"):
                matches = app.query(f"#{widget_id}")
                assert len(matches) == 0, f"Static(id='{widget_id}') should not exist"


class TestSpawnAction:
    """Tests for spawn action (Task #2908)."""

    def test_action_spawn_adds_to_spawning_tasks(self) -> None:
        """action_spawn() adds task to _spawning_tasks with timestamp."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        app = WorkerDashboard(db_path=Path("/tmp/test.db"))
        app._spawning_tasks = {}

        # Mock the sidebar to return spawnable IDs
        mock_sidebar = MagicMock()
        mock_sidebar.selected_task_id = 42
        mock_sidebar.spawnable_ids = [42]

        with (
            patch.object(app, "query_one", return_value=mock_sidebar),
            patch.object(app, "_spawn_task"),
        ):
            app.action_spawn()

        assert 42 in app._spawning_tasks
        assert isinstance(app._spawning_tasks[42], float)



# --- Auto-spawn tests (Task #2765) ---


class TestAutoSpawn:
    """Tests for auto-spawn toggle feature (Task #2765)."""

    @pytest.mark.asyncio
    async def test_auto_spawn_toggle_on_a_key(self) -> None:
        """A key press toggles auto_spawn_enabled True↔False."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        _real_sleep = time.sleep

        def _selective_sleep(seconds: float) -> None:
            if seconds >= 1.0:
                _real_sleep(0.01)
                return
            _real_sleep(seconds)

        app = WorkerDashboard(db_path=Path("/tmp/test.db"))

        with patch("formaltask.apps.dashboard.app.time.sleep", side_effect=_selective_sleep):
            async with app.run_test() as pilot:
                assert app.auto_spawn_enabled is False

                await pilot.press("A")
                await pilot.pause()
                assert app.auto_spawn_enabled is True

                await pilot.press("A")
                await pilot.pause()
                assert app.auto_spawn_enabled is False

    @pytest.mark.asyncio
    async def test_auto_spawn_shows_enabled_indicator(self) -> None:
        """Sidebar title contains 'AUTO' when auto-spawn is enabled."""
        from formaltask.apps.dashboard.app import WorkerDashboard
        from formaltask.apps.dashboard.widgets import TaskList

        _real_sleep = time.sleep
        app = WorkerDashboard(db_path=Path("/tmp/test.db"))

        def _selective_sleep(seconds: float) -> None:
            if seconds >= 1.0:
                _real_sleep(0.01)
                return
            _real_sleep(seconds)

        with patch("formaltask.apps.dashboard.app.time.sleep", side_effect=_selective_sleep):
            async with app.run_test() as pilot:
                await pilot.press("A")
                await pilot.pause()

                sidebar = app.query_one("#task-list", TaskList)
                assert "AUTO" in sidebar.border_title

    @pytest.mark.asyncio
    async def test_auto_spawn_shows_disabled_indicator(self) -> None:
        """Sidebar title does not contain 'AUTO' after toggling off."""
        from formaltask.apps.dashboard.app import WorkerDashboard
        from formaltask.apps.dashboard.widgets import TaskList

        _real_sleep = time.sleep
        app = WorkerDashboard(db_path=Path("/tmp/test.db"))

        def _selective_sleep(seconds: float) -> None:
            if seconds >= 1.0:
                _real_sleep(0.01)
                return
            _real_sleep(seconds)

        with patch("formaltask.apps.dashboard.app.time.sleep", side_effect=_selective_sleep):
            async with app.run_test() as pilot:
                await pilot.press("A")
                await pilot.pause()
                await pilot.press("A")
                await pilot.pause()

                sidebar = app.query_one("#task-list", TaskList)
                assert "AUTO" not in sidebar.border_title

    @pytest.mark.asyncio
    async def test_auto_spawn_worker_cancelled_on_disable(self) -> None:
        """Setting auto_spawn_enabled=False cancels auto_spawn worker."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        _real_sleep = time.sleep
        app = WorkerDashboard(db_path=Path("/tmp/test.db"))

        def _selective_sleep(seconds: float) -> None:
            if seconds >= 1.0:
                _real_sleep(0.01)
                return
            _real_sleep(seconds)

        with patch("formaltask.apps.dashboard.app.time.sleep", side_effect=_selective_sleep):
            async with app.run_test() as pilot:
                await pilot.press("A")
                await pilot.pause()

                # Verify auto_spawn worker exists
                auto_spawn_workers = [w for w in app.workers if w.name == "auto_spawn"]
                assert len(auto_spawn_workers) > 0, "auto_spawn worker should exist when enabled"

                # Disable
                app.auto_spawn_enabled = False
                await pilot.pause()

                # All auto_spawn workers should be cancelled
                for w in auto_spawn_workers:
                    assert w.is_cancelled is True


# --- Auto-spawn orchestrator upgrade tests (Task #2921) ---


class TestAutoSpawnOrchestrated:
    """Tests for auto-spawn orchestrator integration (Task #2921)."""

    @pytest.mark.asyncio
    async def test_auto_spawn_calls_orchestrator_auto_spawn_cycle(self) -> None:
        """Enabling auto-spawn calls orchestrator.auto_spawn_cycle, not old inline logic."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        _real_sleep = time.sleep
        cycle_called = []

        def mock_cycle(db_path: str, max_workers: int, **kwargs) -> list[int]:
            cycle_called.append((db_path, max_workers))
            return []

        def _selective_sleep(seconds: float) -> None:
            if seconds >= 1.0:
                _real_sleep(0.01)
                return
            _real_sleep(seconds)

        app = WorkerDashboard(db_path=Path("/tmp/test.db"))

        with (
            patch("formaltask.apps.dashboard.app.time.sleep", side_effect=_selective_sleep),
            patch("formaltask.apps.dashboard.app.auto_spawn_cycle", side_effect=mock_cycle),
            patch("formaltask.apps.dashboard.app.count_running_workers", return_value=0),
        ):
            async with app.run_test() as pilot:
                await pilot.press("A")
                await pilot.pause()
                # Give the background worker a moment to run
                _real_sleep(0.1)
                await pilot.pause()

                assert len(cycle_called) > 0, "auto_spawn_cycle should have been called"
                assert cycle_called[0][1] == 5, "max_workers should be 5"

    @pytest.mark.asyncio
    async def test_auto_spawn_skips_on_db_error(self) -> None:
        """Auto-spawn skips cycle when count_running_workers returns DB_ERROR."""
        from formaltask.apps.dashboard.app import WorkerDashboard

        _real_sleep = time.sleep
        cycle_called = []

        def mock_cycle(db_path: str, max_workers: int, **kwargs) -> list[int]:
            cycle_called.append(True)
            return []

        def _selective_sleep(seconds: float) -> None:
            if seconds >= 1.0:
                _real_sleep(0.01)
                return
            _real_sleep(seconds)

        app = WorkerDashboard(db_path=Path("/tmp/test.db"))

        with (
            patch("formaltask.apps.dashboard.app.time.sleep", side_effect=_selective_sleep),
            patch("formaltask.apps.dashboard.app.auto_spawn_cycle", side_effect=mock_cycle),
            patch("formaltask.apps.dashboard.app.count_running_workers", return_value=-1),
        ):
            async with app.run_test() as pilot:
                await pilot.press("A")
                await pilot.pause()
                _real_sleep(0.15)
                await pilot.pause()

                assert len(cycle_called) == 0, "auto_spawn_cycle should NOT be called on DB_ERROR"

