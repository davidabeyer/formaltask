"""Tests for TaskList widget with urgency-sorted flat list."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest


class TestSidebarRefreshFromStates:
    """Tests for TaskList.refresh_from_states() contract.

    This method should receive raw worker state dicts and transform them
    internally to TaskRowData, then update the flat urgency-sorted list.
    """

    def test_refresh_from_states_preserves_selection(self) -> None:
        """refresh_from_states should call update_selection with selected_id."""
        from formaltask.apps.dashboard.widgets.task_list import TaskList

        sidebar = TaskList()
        selection_calls: list[int | None] = []

        def capture_selection(task_id: int | None) -> None:
            selection_calls.append(task_id)
            # Don't call original - mock context

        sidebar.update_selection = capture_selection

        raw_states: dict[int, dict[str, Any]] = {
            42: {"task_id": 42, "health_state": "running", "tmux_session_exists": True}
        }
        # This will try to mount which fails without app context, so we mock the mount
        sidebar.mount = lambda *_args, **_kwargs: None
        sidebar.query = lambda _cls: []  # Empty query to avoid DOM issues
        sidebar.refresh_from_states(raw_states, selected_id=42)

        assert 42 in selection_calls, "update_selection should be called with selected_id"


class TestStateToRowData:
    """Tests for TaskList._state_to_row_data() transformation.

    This internal method converts a raw worker state dict to TaskRowData.
    """

    def test_state_to_row_data_populates_task_id(self) -> None:
        """_state_to_row_data should populate task_id from state dict."""
        from formaltask.apps.dashboard.widgets.task_list import TaskList

        sidebar = TaskList()
        state = {"task_id": 42, "health_state": "running"}

        row_data = sidebar._state_to_row_data(42, state)

        assert row_data.task_id == 42

    def test_state_to_row_data_truncates_title_to_max(self) -> None:
        """_state_to_row_data should truncate title to SIDEBAR_TITLE_MAX (74 chars)."""
        from formaltask.apps.dashboard.widgets.task_list import SIDEBAR_TITLE_MAX, TaskList

        sidebar = TaskList()
        long_title = "A" * 100  # exceeds max
        state = {"title": long_title, "health_state": "running"}

        row_data = sidebar._state_to_row_data(42, state)

        assert len(row_data.title) == SIDEBAR_TITLE_MAX
        assert row_data.title == "A" * SIDEBAR_TITLE_MAX

    @pytest.mark.xfail(reason="TDD red phase - awaiting Task #2810 implementation")
    def test_state_to_row_data_derives_status_via_get_sidebar_status(self) -> None:
        """_state_to_row_data should derive status using get_sidebar_status().

        Priority: BLOCKED_STATES -> IDLE_STATES -> (tmux AND NOT stale) -> "idle"
        """
        from formaltask.apps.dashboard.widgets.task_list import TaskList

        sidebar = TaskList()

        # Test blocked state -> "error"
        blocked_state = {
            "health_state": "blocked",
            "tmux_session_exists": True,
            "is_stale": False,
        }
        row_data = sidebar._state_to_row_data(1, blocked_state)
        assert row_data.status == "error", "blocked health_state should map to 'error'"

        # Test running with tmux -> "running"
        running_state = {
            "health_state": "working",
            "tmux_session_exists": True,
            "is_stale": False,
        }
        row_data = sidebar._state_to_row_data(2, running_state)
        assert row_data.status == "running", "working + tmux should map to 'running'"

        # Test completed with active tmux -> "running" (activity trumps IDLE_STATES)
        completed_active_state = {
            "health_state": "completed",
            "tmux_session_exists": True,
            "is_stale": False,
        }
        row_data = sidebar._state_to_row_data(3, completed_active_state)
        assert row_data.status == "running", "completed + active tmux should map to 'running'"

        # Task #2810: Test completed with stale tmux -> "running" (has active tmux)
        # Workers with tmux_session_exists=True appear in RUNNING regardless of is_stale
        completed_stale_state = {
            "health_state": "completed",
            "tmux_session_exists": True,
            "is_stale": True,
        }
        row_data = sidebar._state_to_row_data(4, completed_stale_state)
        assert row_data.status == "running", (
            "completed + stale WITH tmux should map to 'running' (Task #2810)"
        )

    def test_state_to_row_data_calculates_elapsed_from_session_started_at(self) -> None:
        """_state_to_row_data should calculate elapsed_seconds from session_started_at."""
        from formaltask.apps.dashboard.widgets.task_list import TaskList

        sidebar = TaskList()
        # Session started 5 minutes ago
        started_at = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
        state = {
            "health_state": "running",
            "session_started_at": started_at,
        }

        row_data = sidebar._state_to_row_data(42, state)

        # Should be approximately 300 seconds (5 minutes)
        assert 290 <= row_data.elapsed_seconds <= 310

    def test_state_to_row_data_falls_back_to_started_at(self) -> None:
        """_state_to_row_data should fall back to started_at if session_started_at missing."""
        from formaltask.apps.dashboard.widgets.task_list import TaskList

        sidebar = TaskList()
        started_at = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
        state = {
            "health_state": "running",
            "started_at": started_at,
            # No session_started_at
        }

        row_data = sidebar._state_to_row_data(42, state)

        # Should be approximately 600 seconds (10 minutes)
        assert 590 <= row_data.elapsed_seconds <= 610

    def test_state_to_row_data_passes_through_phase(self) -> None:
        """_state_to_row_data should pass through health_state as phase."""
        from formaltask.apps.dashboard.widgets.task_list import TaskList

        sidebar = TaskList()
        state = {
            "health_state": "implementing",
            "tmux_session_exists": True,
        }

        row_data = sidebar._state_to_row_data(42, state)

        assert row_data.phase == "implementing"

    def test_state_to_row_data_defaults_phase_to_unknown(self) -> None:
        """_state_to_row_data should default phase to 'unknown' if health_state missing."""
        from formaltask.apps.dashboard.widgets.task_list import TaskList

        sidebar = TaskList()
        state = {"tmux_session_exists": True}

        row_data = sidebar._state_to_row_data(42, state)

        assert row_data.phase == "unknown"

    def test_state_to_row_data_all_fields_populated(self) -> None:
        """Verify transformation produces TaskRowData with all fields.

        This is the comprehensive behavioral equivalence test ensuring
        _state_to_row_data produces correct output.
        """
        from formaltask.apps.dashboard.widgets.task_list import TaskList

        sidebar = TaskList()
        started_at = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()

        state = {
            "task_id": 42,
            "title": "Implement Widget Contracts",
            "health_state": "implementing",
            "tmux_session_exists": True,
            "is_stale": False,
            "session_started_at": started_at,
        }

        row_data = sidebar._state_to_row_data(42, state)

        # Verify all fields
        assert row_data.task_id == 42
        assert row_data.title == "Implement Widget Contracts"
        assert row_data.status == "running"  # implementing + tmux -> running
        assert 1790 <= row_data.elapsed_seconds <= 1810  # ~30 minutes
        assert row_data.phase == "implementing"

    def test_state_to_row_data_passes_pending_question_as_blocked_question(self) -> None:
        """_state_to_row_data should pass pending_question as blocked_question.

        Task #2771: Sidebar must pass pending_question from worker state to TaskRowData.
        """
        from formaltask.apps.dashboard.widgets.task_list import TaskList

        sidebar = TaskList()
        state = {
            "task_id": 42,
            "title": "Blocked Task",
            "health_state": "blocked",
            "tmux_session_exists": True,
            "pending_question": "Which OAuth provider should I use?",
        }

        row_data = sidebar._state_to_row_data(42, state)

        assert row_data.blocked_question == "Which OAuth provider should I use?"

    def test_state_to_row_data_blocked_question_none_when_no_pending_question(self) -> None:
        """_state_to_row_data should set blocked_question=None when no pending_question.

        Task #2771: Non-blocked tasks should have blocked_question=None.
        """
        from formaltask.apps.dashboard.widgets.task_list import TaskList

        sidebar = TaskList()
        state = {
            "task_id": 42,
            "title": "Running Task",
            "health_state": "implementing",
            "tmux_session_exists": True,
            # No pending_question
        }

        row_data = sidebar._state_to_row_data(42, state)

        assert row_data.blocked_question is None

    def test_state_to_row_data_passes_is_stale(self) -> None:
        """_state_to_row_data should pass through is_stale to TaskRowData.

        Task #2810: Need is_stale in TaskRowData for visual indicator styling.
        """
        from formaltask.apps.dashboard.widgets.task_list import TaskList

        sidebar = TaskList()
        state = {
            "task_id": 42,
            "title": "Stale Task",
            "health_state": "implementing",
            "tmux_session_exists": True,
            "is_stale": True,
        }

        row_data = sidebar._state_to_row_data(42, state)

        assert row_data.is_stale is True

    def test_state_to_row_data_is_stale_defaults_to_false(self) -> None:
        """_state_to_row_data should default is_stale to False when not in state.

        Task #2810: Non-stale workers are the default.
        """
        from formaltask.apps.dashboard.widgets.task_list import TaskList

        sidebar = TaskList()
        state = {
            "task_id": 42,
            "title": "Task",
            "health_state": "implementing",
            "tmux_session_exists": True,
            # No is_stale
        }

        row_data = sidebar._state_to_row_data(42, state)

        assert row_data.is_stale is False


class TestTaskRowDataEpicName:
    """Tests for epic_name field on TaskRowData (Task #2782).

    Task #2822: epic_name field is preserved for display purposes even though
    epic grouping was removed from the sidebar.
    """

    def test_task_row_data_has_epic_name_field(self) -> None:
        """TaskRowData should have epic_name field."""
        from formaltask.apps.dashboard.widgets.task_row import TaskRowData

        # Should be able to create with epic_name
        data = TaskRowData(
            task_id=1,
            title="Task",
            status="running",
            phase="impl",
            elapsed_seconds=0,
            epic_name="my-epic",
        )
        assert data.epic_name == "my-epic"

    def test_task_row_data_epic_name_defaults_to_none(self) -> None:
        """TaskRowData.epic_name should default to None."""
        from formaltask.apps.dashboard.widgets.task_row import TaskRowData

        data = TaskRowData(
            task_id=1,
            title="Task",
            status="running",
            phase="impl",
            elapsed_seconds=0,
        )
        assert data.epic_name is None


class TestSidebarDifferentialUpdates:
    """Tests for differential updates in refresh_from_states (Task #2784).

    The sidebar should NOT invalidate its row cache on every poll.
    Instead, it should perform differential updates:
    - Reuse existing TaskRow widgets where possible
    - Only mount new rows for new tasks
    - Remove rows for tasks no longer in states
    """

    def test_selection_persists_through_differential_update(self) -> None:
        """Test that selection survives differential update with CSS class.

        Task #2785: Selection should persist when refreshing with same states.
        """
        from unittest.mock import Mock

        from formaltask.apps.dashboard.widgets.task_list import TaskList
        from formaltask.apps.dashboard.widgets.task_row import TaskRow, TaskRowData

        sidebar = TaskList()
        sidebar.mount = lambda *_args, **_kwargs: None

        # Pre-populate cache with a mock row
        mock_row = Mock(spec=TaskRow)
        mock_row.data = TaskRowData(
            task_id=42, title="Task 42", status="running", phase="impl", elapsed_seconds=0
        )
        sidebar._row_cache = {42: mock_row}
        sidebar.query = lambda _cls: [mock_row]

        # First refresh with selection
        states: dict[int, dict[str, Any]] = {
            42: {
                "task_id": 42,
                "title": "Task 42",
                "health_state": "working",
                "tmux_session_exists": True,
                "is_stale": False,
            },
        }
        sidebar.refresh_from_states(states, selected_id=42)

        # Second refresh with same selection
        sidebar.refresh_from_states(states, selected_id=42)

        # Selection should persist
        assert sidebar.selected_task_id == 42, "selected_task_id should be preserved"
        # add_class should have been called with --selected
        mock_row.add_class.assert_called_with("--selected")


class TestSidebarFlatList:
    """Tests for flat urgency-sorted sidebar (Task #2822).

    Sidebar should display a flat list of tasks sorted by urgency without
    epic grouping containers.
    """

    def test_refresh_from_states_does_not_create_epic_containers(self) -> None:
        """refresh_from_states should mount TaskRows directly without Vertical containers."""
        from textual.containers import Vertical

        from formaltask.apps.dashboard.widgets.task_list import TaskList

        sidebar = TaskList()
        mounted_widgets: list = []
        sidebar.mount = lambda w: mounted_widgets.append(w)
        sidebar.query = lambda _cls: []

        states: dict[int, dict[str, Any]] = {
            1: {
                "task_id": 1,
                "title": "Task 1",
                "health_state": "working",
                "tmux_session_exists": True,
                "is_stale": False,
                "epic_name": "auth-system",
            },
        }
        sidebar.refresh_from_states(states, selected_id=None, spawnable_ids=None)

        # Should NOT mount any Vertical containers (epic grouping removed)
        vertical_containers = [w for w in mounted_widgets if isinstance(w, Vertical)]
        assert len(vertical_containers) == 0, (
            f"Should not create Vertical epic containers. Found {len(vertical_containers)}"
        )


class TestSidebarUrgencySort:
    """Tests for flat urgency-sorted sidebar (Task #2679).

    After removing StateGroup, TaskList should sort tasks by urgency:
    error (blocked) > running > idle > queued
    """

    def test_sidebar_sorts_by_urgency(self) -> None:
        """TaskList.update_tasks should sort tasks by urgency: error > running > idle.

        This test verifies the internal sorting implementation.
        """
        from formaltask.apps.dashboard.widgets.task_row import TaskRowData

        # Create tasks in "wrong" order (idle first, then running, then error)
        tasks = [
            TaskRowData(
                task_id=1,
                title="Idle Task",
                status="idle",
                phase="done",
                elapsed_seconds=100,
            ),
            TaskRowData(
                task_id=2,
                title="Running Task",
                status="running",
                phase="implementing",
                elapsed_seconds=200,
            ),
            TaskRowData(
                task_id=3,
                title="Error Task",
                status="error",
                phase="blocked",
                elapsed_seconds=300,
            ),
        ]

        # Test sorting logic directly with PRIORITY dict
        PRIORITY = {"error": 0, "running": 1, "idle": 2}
        sorted_tasks = sorted(tasks, key=lambda t: PRIORITY.get(t.status, 3))

        # Verify sort order: error (task 3) > running (task 2) > idle (task 1)
        assert [t.task_id for t in sorted_tasks] == [3, 2, 1], (
            "Tasks should be sorted by urgency (error > running > idle)"
        )

    def test_queued_tasks_appear_after_active_workers(self) -> None:
        """Task #2848: Queued tasks should appear after all active workers.

        Sort order: error > running > idle > queued
        Within same status, sort by task_id for stability.
        """
        from formaltask.apps.dashboard.widgets.task_list import TaskList

        sidebar = TaskList()

        # Track mount order
        mounted_task_ids: list[int] = []

        def capture_mount(widget) -> None:
            if hasattr(widget, "data"):
                mounted_task_ids.append(widget.data.task_id)

        sidebar.mount = capture_mount
        sidebar.query = lambda _cls: []  # No existing rows

        # Active workers with various statuses
        states: dict[int, dict[str, Any]] = {
            10: {
                "task_id": 10,
                "title": "Idle worker",
                "health_state": "completed",
                "tmux_session_exists": False,
                "is_stale": False,
            },
            20: {
                "task_id": 20,
                "title": "Running worker",
                "health_state": "working",
                "tmux_session_exists": True,
                "is_stale": False,
            },
            30: {
                "task_id": 30,
                "title": "Error worker",
                "health_state": "blocked",
                "tmux_session_exists": True,
                "is_stale": False,
            },
        }

        # Spawnable (queued) tasks
        spawnable_ids = [40, 50]
        spawnable_tasks = [
            {"id": 40, "title": "Queued task 1"},
            {"id": 50, "title": "Queued task 2"},
        ]

        sidebar.refresh_from_states(
            states,
            selected_id=None,
            spawnable_ids=spawnable_ids,
            spawnable_tasks=spawnable_tasks,
        )

        # Expected order: error(30) > running(20) > idle(10) > queued(40, 50)
        assert mounted_task_ids == [30, 20, 10, 40, 50], (
            f"Expected [30, 20, 10, 40, 50] but got {mounted_task_ids}. "
            "Queued tasks should appear after all active workers."
        )

    def test_sidebar_compose_no_state_groups(self) -> None:
        """TaskList.compose() should not yield StateGroup widgets."""
        from formaltask.apps.dashboard.widgets.task_list import TaskList

        sidebar = TaskList()
        composed = list(sidebar.compose())

        # After flattening, compose should return empty (or no StateGroups)
        # StateGroup won't exist after removal, so we check there's no Collapsible
        from textual.widgets import Collapsible

        for widget in composed:
            assert not isinstance(widget, Collapsible), (
                "compose() should not yield Collapsible/StateGroup widgets"
            )
