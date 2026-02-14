"""Tests for watch.py daemon cycle after auto_spawn_cycle unification.

The watch daemon delegates spawn logic to auto_spawn_cycle in orchestrator.py.
These tests verify _daemon_cycle correctly delegates and handles return values.
"""

import pytest

from formaltask.cli.commands import watch as watch_module


@pytest.fixture(autouse=True)
def mock_common_deps(monkeypatch):
    """Stub deps shared across all tests."""
    monkeypatch.setattr(watch_module, "get_orphaned_workers", lambda db_path=None: [])


class TestSpawnDelegation:
    """Test that _daemon_cycle delegates to auto_spawn_cycle."""

    def test_spawn_enabled_calls_auto_spawn_cycle(self, monkeypatch, tmp_path):
        """spawn_enabled=True delegates to auto_spawn_cycle with max_workers."""
        db_path = str(tmp_path / "test.db")
        cycle_calls = []

        def mock_cycle(dp, mw, **kwargs):
            cycle_calls.append((dp, mw, kwargs))
            return []

        monkeypatch.setattr(watch_module, "auto_spawn_cycle", mock_cycle)
        monkeypatch.setattr(watch_module, "count_running_workers", lambda: 0)
        monkeypatch.setattr(watch_module, "get_spawnable_tasks", lambda _p: [])

        watch_module._daemon_cycle(
            db_path=db_path, max_workers=5,
            spawn_enabled=True, modes=["watch", "spawn"], interval=10,
        )

        assert len(cycle_calls) == 1
        assert cycle_calls[0][0] == db_path
        assert cycle_calls[0][1] == 5
        assert cycle_calls[0][2]["check_supervisor"] is True
        assert cycle_calls[0][2]["orchestration_rules"] is not None

    def test_spawn_disabled_calls_with_zero_max(self, monkeypatch, tmp_path):
        """spawn_enabled=False calls auto_spawn_cycle with max_workers=0."""
        db_path = str(tmp_path / "test.db")
        cycle_calls = []

        def mock_cycle(dp, mw, **kwargs):
            cycle_calls.append((dp, mw))
            return []

        monkeypatch.setattr(watch_module, "auto_spawn_cycle", mock_cycle)
        monkeypatch.setattr(watch_module, "count_running_workers", lambda: 0)

        watch_module._daemon_cycle(
            db_path=db_path, max_workers=5,
            spawn_enabled=False, modes=["watch"], interval=10,
        )

        assert len(cycle_calls) == 1
        assert cycle_calls[0][1] == 0  # max_workers=0

    def test_db_error_returns_early(self, monkeypatch, tmp_path):
        """DB_ERROR from count_running_workers skips cycle entirely."""
        db_path = str(tmp_path / "test.db")
        cycle_called = False

        def mock_cycle(*a, **kw):
            nonlocal cycle_called
            cycle_called = True
            return []

        monkeypatch.setattr(watch_module, "auto_spawn_cycle", mock_cycle)
        monkeypatch.setattr(watch_module, "count_running_workers", lambda: watch_module.DB_ERROR)

        watch_module._daemon_cycle(
            db_path=db_path, max_workers=5,
            spawn_enabled=True, modes=["watch", "spawn"], interval=10,
        )

        assert cycle_called is False

    def test_spawned_tasks_trigger_status_block(self, monkeypatch, tmp_path):
        """When auto_spawn_cycle returns spawned IDs, status block is printed."""
        db_path = str(tmp_path / "test.db")
        status_calls = []

        def mock_cycle(*a, **kw):
            return [101, 102]

        def mock_status(*args, **kwargs):
            status_calls.append(args)

        monkeypatch.setattr(watch_module, "auto_spawn_cycle", mock_cycle)
        monkeypatch.setattr(watch_module, "count_running_workers", lambda: 0)
        monkeypatch.setattr(watch_module, "_print_status_block", mock_status)

        watch_module._daemon_cycle(
            db_path=db_path, max_workers=5,
            spawn_enabled=True, modes=["watch", "spawn"], interval=10,
        )

        assert len(status_calls) == 1


class TestSpawnDelay:
    """Test spawn delay timing (10s between daemon cycles)."""

    def test_execute_sleeps_for_interval(self, monkeypatch, tmp_path):
        """Verify time.sleep called with 10 (default interval)."""
        import time

        db_path = str(tmp_path / "test.db")
        sleep_calls = []

        def mock_sleep(seconds):
            sleep_calls.append(seconds)
            raise KeyboardInterrupt()

        monkeypatch.setattr(time, "sleep", mock_sleep)
        monkeypatch.setattr(watch_module, "_daemon_cycle", lambda *a, **kw: None)
        monkeypatch.setattr(watch_module, "_setup_logging", lambda _f: None)
        monkeypatch.setattr(watch_module, "_print_status_block", lambda *a, **kw: None)

        class MockArgs:
            interval = 10
            log_file = str(tmp_path / "watch.log")
            spawn = False
            cleanup = False
            max_workers = 5

        # Call the unwrapped function directly (bypass @with_db_path)
        result = watch_module.execute.__wrapped__(db_path, MockArgs())

        assert sleep_calls == [10]
        assert result == 0
