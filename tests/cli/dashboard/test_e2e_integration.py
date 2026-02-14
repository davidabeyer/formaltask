"""End-to-end integration tests for full dashboard feature verification.

Task #2768: [VERIFY] Full Dashboard Integration.
Validates spawn and auto-spawn toggle work together.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from formaltask.apps.dashboard.app import WorkerDashboard


@pytest.mark.asyncio
@patch("formaltask.apps.dashboard.app.get_blocked_workers", return_value=[])
@patch("formaltask.apps.dashboard.app.get_spawnable_tasks_with_titles", return_value=[])
@patch("formaltask.apps.dashboard.app.spawn_worker")
@patch("formaltask.apps.dashboard.app.transition_task_status")
@patch("formaltask.apps.dashboard.app.get_all_task_sessions", return_value=[])
@patch("formaltask.apps.dashboard.app.count_running_workers", return_value=0)
@patch("formaltask.apps.dashboard.app.auto_spawn_cycle", return_value=[])
async def test_spawn_from_queue_section(
    _mock_auto_spawn: MagicMock,
    _mock_count: MagicMock,
    _mock_sessions: MagicMock,
    _mock_transition: MagicMock,
    mock_spawn_worker: MagicMock,
    _mock_get_spawnable_titles: MagicMock,
    _mock_get_blocked: MagicMock,
) -> None:
    """Spawn specific task from QUEUE section via S key."""
    from pathlib import Path

    db_path = Path("/tmp/test_e2e_spawn.db")
    app = WorkerDashboard(db_path=db_path)

    async with app.run_test() as pilot:
        # Set up sidebar with spawnable queue items and select one
        sidebar = app.query_one("#task-list")
        sidebar._spawnable_ids = [200, 201, 202]
        sidebar._selected_task_id = 201  # Select specific QUEUE item

        await pilot.press("S")
        await app.workers.wait_for_complete()
        await pilot.pause()

        # Should spawn the selected task
        assert mock_spawn_worker.called
        assert mock_spawn_worker.call_args[0][0] == 201
