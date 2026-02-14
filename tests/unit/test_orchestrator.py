"""Tests for formaltask.workers.orchestrator module."""



class TestOrchestratorExports:
    """Verify orchestrator module exports all required functions."""

    def test_exports_evaluate_orchestration_rules(self):
        from formaltask.workers.orchestrator import evaluate_orchestration_rules

        assert callable(evaluate_orchestration_rules)

    def test_exports_send_notification(self):
        from formaltask.workers.orchestrator import send_notification

        assert callable(send_notification)

    def test_exports_count_running_workers(self):
        from formaltask.workers.orchestrator import count_running_workers

        assert callable(count_running_workers)

    def test_exports_auto_spawn_cycle(self):
        from formaltask.workers.orchestrator import auto_spawn_cycle

        assert callable(auto_spawn_cycle)

    def test_exports_spawn_supervisor_if_needed(self):
        from formaltask.workers.orchestrator import spawn_supervisor_if_needed

        assert callable(spawn_supervisor_if_needed)


class TestAutoSpawnRespectMaxWorkers:
    """auto_spawn_cycle must not spawn when running >= max_workers."""

    def test_auto_spawn_no_spawn_when_at_max(self, monkeypatch):
        """When running workers >= max_workers, no tasks are spawned."""
        from formaltask.workers import orchestrator

        spawn_called = False

        def mock_get_spawnable(_path):
            return [101]

        def mock_count():
            return 5  # At max

        def mock_spawn(_task_id, _path):
            nonlocal spawn_called
            spawn_called = True

        monkeypatch.setattr(orchestrator, "get_spawnable_tasks", mock_get_spawnable)
        monkeypatch.setattr(orchestrator, "count_running_workers", mock_count)
        monkeypatch.setattr(orchestrator, "spawn_worker", mock_spawn)

        result = orchestrator.auto_spawn_cycle("fake.db", max_workers=5)

        assert spawn_called is False
        assert result == []


class TestAutoSpawnErrorRecovery:
    """auto_spawn_cycle must reset task status to 'open' on SpawnError."""

    def test_spawn_error_resets_status(self, monkeypatch):
        """On SpawnError, transition_task_status is called with 'open' and force=True."""
        from formaltask.workers import orchestrator
        from formaltask.workers.spawner import SpawnError

        transition_calls = []

        def mock_get_spawnable(_path):
            return [101]

        def mock_count():
            return 0

        def mock_transition(_path, task_id, status, force=False):
            transition_calls.append((task_id, status, force))

        def mock_spawn(_task_id, _path):
            raise SpawnError("test error")

        monkeypatch.setattr(orchestrator, "get_spawnable_tasks", mock_get_spawnable)
        monkeypatch.setattr(orchestrator, "count_running_workers", mock_count)
        monkeypatch.setattr(orchestrator, "transition_task_status", mock_transition)
        monkeypatch.setattr(orchestrator, "spawn_worker", mock_spawn)

        orchestrator.auto_spawn_cycle("fake.db", max_workers=5)

        # First: transition to in_progress, Second: reset to open (force=True)
        assert transition_calls == [(101, "in_progress", False), (101, "open", True)]
