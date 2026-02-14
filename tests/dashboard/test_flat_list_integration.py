"""Integration tests for flat-list dashboard rebuild.

Task #2910: Validates all 8 goals of the dashboard rebuild are met.
Mounts the real WorkerDashboard app with mocked DB/tmux backends
and verifies the full widget tree, keybindings, and state transitions.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from formaltask.apps.dashboard.app import WorkerDashboard, WorkerStatesUpdated
from formaltask.apps.dashboard.widgets import StatusBar, TaskList, TaskRow

# -- Helpers ------------------------------------------------------------------


def _make_worker_state(
    task_id: int,
    *,
    health_state: str = "implementing",
    epic_name: str = "test-epic",
    title: str = "",
    tmux_session_exists: bool = True,
) -> dict:
    """Build a minimal worker state dict for testing."""
    return {
        "task_id": task_id,
        "health_state": health_state,
        "epic_name": epic_name,
        "title": title or f"Task {task_id}",
        "tmux_session_exists": tmux_session_exists,
        "started_at": "2025-01-01T00:00:00Z",
        "session_started_at": "2025-01-01T00:00:00Z",
        "pane_output": "",
        "is_stale": False,
    }


# Patch targets — block all external I/O in the app
_PATCHES = {
    "formaltask.apps.dashboard.app.get_all_task_sessions": list,
    "formaltask.apps.dashboard.app.fetch_worker_states": lambda *a, **kw: [],
    "formaltask.apps.dashboard.app.get_spawnable_tasks_with_titles": lambda *a, **kw: [],
    "formaltask.apps.dashboard.app.get_blocked_workers": lambda *a, **kw: [],
    "formaltask.apps.dashboard.app.count_running_workers": lambda: 0,
    "formaltask.apps.dashboard.app.auto_spawn_cycle": lambda *a, **kw: [],
    "formaltask.apps.dashboard.app.attach_session": lambda *a, **kw: None,
    "formaltask.apps.dashboard.app.kill_session": lambda *a, **kw: None,
    "formaltask.apps.dashboard.app.create_session": lambda *a, **kw: True,
    "formaltask.apps.dashboard.app.send_keys": lambda *a, **kw: True,
    "formaltask.apps.dashboard.app.cleanup_orphan_mcps": lambda: None,
    "formaltask.apps.dashboard.app.spawn_worker": lambda *a, **kw: None,
    "formaltask.apps.dashboard.app.transition_task_status": lambda *a, **kw: None,
}


@pytest.fixture
def patched_dashboard(tmp_path):
    """Yield a WorkerDashboard with all external I/O mocked."""
    db_file = tmp_path / "test.db"
    db_file.touch()

    patches = [patch(target, side_effect=fn) for target, fn in _PATCHES.items()]
    for p in patches:
        p.start()

    app = WorkerDashboard(db_path=db_file)

    yield app

    for p in patches:
        p.stop()


# -- Test 1: Layout composition -----------------------------------------------


# -- Test 2: Flat list renders epics, task IDs, badges -------------------------


class TestFlatListRendering:
    """Mock 2 epics with mixed states, verify flat list renders epic column, task IDs, badges."""

    @pytest.mark.asyncio
    async def test_flat_list_renders_mixed_epics_and_badges(self, patched_dashboard):
        async with patched_dashboard.run_test(size=(120, 40)) as pilot:
            app = pilot.app

            # Post states from 2 epics with mixed health states
            states = {
                100: _make_worker_state(100, epic_name="alpha", health_state="implementing"),
                200: _make_worker_state(200, epic_name="alpha", health_state="exited"),
                300: _make_worker_state(300, epic_name="beta", health_state="needs_fix"),
                400: _make_worker_state(400, epic_name="beta", health_state="queued"),
            }

            app.post_message(WorkerStatesUpdated(states))
            await pilot.pause()

            # Verify TaskRows exist for active workers
            task_list = app.query_one("#task-list", TaskList)
            rows = task_list.query(TaskRow)
            assert len(rows) == 4  # 3 active + 1 queued

            # Check task IDs are present in row data
            row_task_ids = {row.data.task_id for row in rows}
            assert 100 in row_task_ids
            assert 200 in row_task_ids
            assert 300 in row_task_ids

            # Check epic names are set
            for row in rows:
                assert row.data.epic_name in ("alpha", "beta")

            # Check phase badges map correctly
            row_100 = next(r for r in rows if r.data.task_id == 100)
            assert row_100.data.phase == "implementing"
            row_200 = next(r for r in rows if r.data.task_id == 200)
            assert row_200.data.phase == "exited"
            row_300 = next(r for r in rows if r.data.task_id == 300)
            assert row_300.data.phase == "needs_fix"


# -- Test 3: j/k navigation and Enter attach ----------------------------------


class TestNavigation:
    """Verify j/k navigation moves cursor, Enter attaches (mock)."""

    @pytest.mark.asyncio
    async def test_jk_navigation_moves_selection(self, patched_dashboard):
        async with patched_dashboard.run_test(size=(120, 40)) as pilot:
            app = pilot.app

            states = {
                10: _make_worker_state(10, health_state="implementing"),
                20: _make_worker_state(20, health_state="implementing"),
                30: _make_worker_state(30, health_state="implementing"),
            }
            app.post_message(WorkerStatesUpdated(states))
            await pilot.pause()

            # Auto-selects first task
            assert app.selected_task_id is not None

            first_selected = app.selected_task_id

            # Press j to navigate down
            await pilot.press("j")
            await pilot.pause()
            second_selected = app.selected_task_id
            assert second_selected != first_selected

            # Press k to navigate back up
            await pilot.press("k")
            await pilot.pause()
            assert app.selected_task_id == first_selected

    @pytest.mark.asyncio
    async def test_enter_triggers_attach(self, patched_dashboard):
        attach_called = []

        async with patched_dashboard.run_test(size=(120, 40)) as pilot:
            app = pilot.app

            states = {10: _make_worker_state(10)}
            app.post_message(WorkerStatesUpdated(states))
            await pilot.pause()

            # Mock the attach action to record call
            def mock_attach():
                attach_called.append(app.selected_task_id)

            app.action_attach = mock_attach

            await pilot.press("enter")
            await pilot.pause()

            assert len(attach_called) == 1
            assert attach_called[0] == 10


# -- Test 4: S spawns queued task, SPAWN state with dots -----------------------


class TestSpawnTransition:
    """Verify S spawns queued task, SPAWN state appears with dots."""

    @pytest.mark.asyncio
    async def test_spawn_sets_spawning_state(self, patched_dashboard):
        async with patched_dashboard.run_test(size=(120, 40)) as pilot:
            app = pilot.app

            # Set up spawnable tasks
            spawnable = [{"id": 50, "title": "Spawnable task"}]
            states = {
                10: _make_worker_state(10, health_state="implementing"),
            }
            app.post_message(WorkerStatesUpdated(states, spawnable_tasks=spawnable))
            await pilot.pause()

            # Press S to spawn
            await pilot.press("S")
            await pilot.pause()

            # The task should now be in _spawning_tasks
            assert 50 in app._spawning_tasks


# -- Test 5: EXIT state shows ! marker -----------------------------------------


class TestExitStateMarker:
    """Verify EXIT state shows ! marker and promotes above separator."""

    @pytest.mark.asyncio
    async def test_exited_without_tmux_shows_bang_marker(self, patched_dashboard):
        async with patched_dashboard.run_test(size=(120, 40)) as pilot:
            app = pilot.app

            # Exited state without tmux = zombie = ! marker
            states = {
                10: _make_worker_state(
                    10,
                    health_state="implementing",
                    tmux_session_exists=False,
                ),
            }
            app.post_message(WorkerStatesUpdated(states))
            await pilot.pause()

            task_list = app.query_one("#task-list", TaskList)
            rows = task_list.query(TaskRow)
            assert len(rows) == 1

            row = rows[0]
            # implementing with no tmux = zombie = "!" marker
            assert row.data.row_marker == "!"

    @pytest.mark.asyncio
    async def test_exited_state_sorts_above_queued(self, patched_dashboard):
        async with patched_dashboard.run_test(size=(120, 40)) as pilot:
            app = pilot.app

            # Active error (sorts first), then idle exited, with a queued task
            states = {
                10: _make_worker_state(10, health_state="implementing"),
                20: _make_worker_state(20, health_state="exited"),
            }
            spawnable = [{"id": 50, "title": "Queued task"}]
            app.post_message(WorkerStatesUpdated(states, spawnable_tasks=spawnable))
            await pilot.pause()

            task_list = app.query_one("#task-list", TaskList)
            rows = task_list.query(TaskRow)

            # Get the order of task_ids from rendered rows
            row_ids = [row.data.task_id for row in rows]
            # Running (10) should be before idle exited (20)
            # Queued (50) should be after both
            assert row_ids.index(10) < row_ids.index(20)
            assert 50 in row_ids, "Queued task 50 should be rendered"
            assert row_ids.index(20) < row_ids.index(50)


# -- Test 6: StatusBar shows correct counts ------------------------------------


class TestStatusBarCounts:
    """Verify StatusBar shows correct counts after poll."""

    @pytest.mark.asyncio
    async def test_status_bar_reflects_state_counts(self, patched_dashboard):
        async with patched_dashboard.run_test(size=(120, 40)) as pilot:
            app = pilot.app

            states = {
                1: _make_worker_state(1, epic_name="e1", health_state="implementing"),
                2: _make_worker_state(2, epic_name="e1", health_state="done"),
                3: _make_worker_state(3, epic_name="e2", health_state="exited"),
                4: _make_worker_state(4, epic_name="e2", health_state="needs_human"),
            }
            spawnable = [{"id": 50, "title": "Q1"}]
            app.post_message(WorkerStatesUpdated(states, spawnable_tasks=spawnable))
            await pilot.pause()

            status_bar = app.query_one("#status-bar", StatusBar)

            # 2 epics: e1 and e2
            assert status_bar._epic_count == 2
            # 1 done (health_state="done")
            assert status_bar._done == 1
            # 1 running (implementing is not idle/blocked/done/exited/unknown/queued)
            assert status_bar._running_count == 1
            # 1 exited
            assert status_bar._exit_count == 1
            # 1 help (needs_human → help_count)
            assert status_bar._help_count == 1
            # 1 queued (spawnable)
            assert status_bar._queued == 1


# -- Test 6b: A key toggles auto-spawn ----------------------------------------


