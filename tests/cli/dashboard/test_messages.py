"""Tests for dashboard domain messages (Task #2594).

Contract tests for message attributes that handlers depend on.
Import and isinstance tests removed - redundant with usage.
"""


class TestWorkerStatesUpdated:
    """Tests for WorkerStatesUpdated message contract."""

    def test_worker_states_updated_carries_states(self):
        """Message should carry worker states dict."""
        from formaltask.apps.dashboard.app import WorkerStatesUpdated

        states = {
            1: {"task_id": 1, "health_state": "running"},
            2: {"task_id": 2, "health_state": "idle"},
        }
        msg = WorkerStatesUpdated(states)

        assert msg.states == states


class TestWorkerStateChanged:
    """Tests for WorkerStateChanged message contract."""

    def test_worker_state_changed_carries_transition(self):
        """Message should carry task_id, from_state, to_state, and worker dict."""
        from formaltask.apps.dashboard.app import WorkerStateChanged

        worker = {"task_id": 42, "health_state": "error", "task_title": "Fix bug"}
        msg = WorkerStateChanged(
            task_id=42,
            from_state="running",
            to_state="error",
            worker=worker,
        )

        assert msg.task_id == 42
        assert msg.from_state == "running"
        assert msg.to_state == "error"
        assert msg.worker == worker


class TestWorkerKilled:
    """Tests for WorkerKilled message contract."""

    def test_worker_killed_carries_task_and_next(self):
        """Message should carry task_id and next_task_id."""
        from formaltask.apps.dashboard.app import WorkerKilled

        msg = WorkerKilled(task_id=42, next_task_id=43)

        assert msg.task_id == 42
        assert msg.next_task_id == 43

    def test_worker_killed_next_task_id_can_be_none(self):
        """next_task_id should accept None."""
        from formaltask.apps.dashboard.app import WorkerKilled

        msg = WorkerKilled(task_id=42, next_task_id=None)

        assert msg.task_id == 42
        assert msg.next_task_id is None
