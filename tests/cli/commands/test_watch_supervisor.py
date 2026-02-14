"""Tests for watch daemon supervisor integration.

Task #2886: Watch spawns supervisor when blocked workers exist,
kills stale supervisor (pane dead), respects existing supervisor.
"""

import pytest

from formaltask.cli.commands import watch as watch_module
from formaltask.workers import orchestrator as orchestrator_module


@pytest.fixture(autouse=True)
def mock_orchestration_deps(monkeypatch):
    """Mock orchestrator deps so spawn cycle doesn't hit real DB/tmux."""
    monkeypatch.setattr(
        orchestrator_module, "evaluate_orchestration_rules", lambda _db, _rules: None
    )
    monkeypatch.setattr(orchestrator_module, "get_spawnable_tasks", lambda _db: [])
    monkeypatch.setattr(
        orchestrator_module, "transition_task_status", lambda *a, **kw: None
    )


class TestSupervisorSpawn:
    """Test supervisor spawn logic in _daemon_cycle."""

    def test_spawns_supervisor_when_blocked_workers_exist(self, monkeypatch, tmp_path):
        """When blocked workers exist and no supervisor session, spawn supervisor."""
        db_path = str(tmp_path / ".claude" / "formaltask.db")
        tmux_calls = []

        def mock_count_running():
            return 0

        def mock_get_orphaned(db_path=None):
            return []

        def mock_get_blocked(_db_path):
            return [{"task_id": 101, "question": "Help needed"}]

        def mock_session_exists(name):
            return False  # No supervisor yet

        def mock_is_pane_alive(name):
            return False

        def mock_kill_session(name):
            tmux_calls.append(("kill", name))
            return True

        def mock_create_session(name, cwd, env_vars=None, timeout=30):
            tmux_calls.append(("create", name, cwd, env_vars))
            return True

        def mock_send_keys(name, keys):
            tmux_calls.append(("send_keys", name, keys))
            return True

        # Patch watch_module bindings (used by _daemon_cycle directly)
        monkeypatch.setattr(watch_module, "count_running_workers", mock_count_running)
        monkeypatch.setattr(watch_module, "get_orphaned_workers", mock_get_orphaned)

        # Patch orchestrator internals (used by spawn_supervisor_if_needed)
        monkeypatch.setattr(orchestrator_module, "get_blocked_workers", mock_get_blocked)
        monkeypatch.setattr(orchestrator_module.tmux, "session_exists", mock_session_exists)
        monkeypatch.setattr(orchestrator_module.tmux, "is_pane_alive", mock_is_pane_alive)
        monkeypatch.setattr(orchestrator_module.tmux, "kill_session", mock_kill_session)
        monkeypatch.setattr(orchestrator_module.tmux, "create_session", mock_create_session)
        monkeypatch.setattr(orchestrator_module.tmux, "send_keys", mock_send_keys)

        watch_module._daemon_cycle(
            db_path=db_path,
            max_workers=5,
            spawn_enabled=False,
            modes=["watch"],
            interval=10,
        )

        # Should create supervisor session
        assert len(tmux_calls) >= 2
        create_call = [c for c in tmux_calls if c[0] == "create"]
        assert len(create_call) == 1
        assert create_call[0][1] == "supervisor"
        assert create_call[0][3] == {"SUPERVISOR_UNATTENDED": "1"}

        # Should send keys to start claude
        send_keys_call = [c for c in tmux_calls if c[0] == "send_keys"]
        assert len(send_keys_call) == 1
        assert "supervisor" in send_keys_call[0][2]

    def test_does_not_spawn_supervisor_if_already_running(self, monkeypatch, tmp_path):
        """When supervisor session already exists, do not spawn another."""
        db_path = str(tmp_path / ".claude" / "formaltask.db")
        tmux_calls = []

        def mock_count_running():
            return 0

        def mock_get_orphaned(db_path=None):
            return []

        def mock_get_blocked(_db_path):
            return [{"task_id": 101, "question": "Help needed"}]

        def mock_session_exists(name):
            return name == "supervisor"  # Supervisor exists

        def mock_is_pane_alive(name):
            return True  # Pane is alive

        def mock_create_session(name, cwd, env_vars=None, timeout=30):
            tmux_calls.append(("create", name))
            return True

        # Patch watch_module bindings
        monkeypatch.setattr(watch_module, "count_running_workers", mock_count_running)
        monkeypatch.setattr(watch_module, "get_orphaned_workers", mock_get_orphaned)

        # Patch orchestrator internals
        monkeypatch.setattr(orchestrator_module, "get_blocked_workers", mock_get_blocked)
        monkeypatch.setattr(orchestrator_module.tmux, "session_exists", mock_session_exists)
        monkeypatch.setattr(orchestrator_module.tmux, "is_pane_alive", mock_is_pane_alive)
        monkeypatch.setattr(orchestrator_module.tmux, "create_session", mock_create_session)

        watch_module._daemon_cycle(
            db_path=db_path,
            max_workers=5,
            spawn_enabled=False,
            modes=["watch"],
            interval=10,
        )

        # Should NOT create a new supervisor session
        create_calls = [c for c in tmux_calls if c[0] == "create"]
        assert len(create_calls) == 0

    def test_kills_stale_supervisor_session(self, monkeypatch, tmp_path):
        """When supervisor session exists but pane is dead, kill it and respawn."""
        db_path = str(tmp_path / ".claude" / "formaltask.db")
        tmux_calls = []

        def mock_count_running():
            return 0

        def mock_get_orphaned(db_path=None):
            return []

        def mock_get_blocked(_db_path):
            return [{"task_id": 101, "question": "Help needed"}]

        def mock_session_exists(name):
            return name == "supervisor"  # Supervisor session exists

        def mock_is_pane_alive(name):
            return False  # But pane is dead (Claude exited)

        def mock_kill_session(name):
            tmux_calls.append(("kill", name))
            return True

        def mock_create_session(name, cwd, env_vars=None, timeout=30):
            tmux_calls.append(("create", name, cwd, env_vars))
            return True

        def mock_send_keys(name, keys):
            tmux_calls.append(("send_keys", name, keys))
            return True

        # Patch watch_module bindings
        monkeypatch.setattr(watch_module, "count_running_workers", mock_count_running)
        monkeypatch.setattr(watch_module, "get_orphaned_workers", mock_get_orphaned)

        # Patch orchestrator internals
        monkeypatch.setattr(orchestrator_module, "get_blocked_workers", mock_get_blocked)
        monkeypatch.setattr(orchestrator_module.tmux, "session_exists", mock_session_exists)
        monkeypatch.setattr(orchestrator_module.tmux, "is_pane_alive", mock_is_pane_alive)
        monkeypatch.setattr(orchestrator_module.tmux, "kill_session", mock_kill_session)
        monkeypatch.setattr(orchestrator_module.tmux, "create_session", mock_create_session)
        monkeypatch.setattr(orchestrator_module.tmux, "send_keys", mock_send_keys)

        watch_module._daemon_cycle(
            db_path=db_path,
            max_workers=5,
            spawn_enabled=False,
            modes=["watch"],
            interval=10,
        )

        # Should kill stale session first
        kill_calls = [c for c in tmux_calls if c[0] == "kill"]
        assert len(kill_calls) == 1
        assert kill_calls[0][1] == "supervisor"

        # Then create new supervisor session
        create_calls = [c for c in tmux_calls if c[0] == "create"]
        assert len(create_calls) == 1
        assert create_calls[0][1] == "supervisor"
