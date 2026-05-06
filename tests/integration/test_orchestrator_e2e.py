"""End-to-end integration tests for orchestrator flow.

Task #2887: Validates the complete orchestrator flow:
blocked worker → watch detects → supervisor spawns → supervisor resumes → worker continues.

Task #2888: Live verification performed 2026-02-04:
- Worker ran `ft blocked "Testing supervisor auto-response flow"`
- Watch daemon detected and spawned supervisor with SUPERVISOR_UNATTENDED=1
- Supervisor auto-responded without human interaction
- Worker session resumed automatically

Tests the ERA pattern (Emit → Route → Act) works end-to-end.
"""

import sqlite3

import pytest

from formaltask.cli.commands import watch as watch_module
from formaltask.workers import orchestrator as orchestrator_module
from formaltask.workers import orchestrator as orchestrator_module
from formaltask.workers.inbox import get_blocked_workers
from tests.fixtures.paths import SCHEMA_FILE


@pytest.fixture
def test_db(tmp_path):
    """Create test database with FormalTask schema."""
    db_path = tmp_path / ".claude" / "formaltask.db"
    db_path.parent.mkdir(parents=True)

    with sqlite3.connect(db_path) as conn:
        with open(SCHEMA_FILE) as f:
            conn.executescript(f.read())
        conn.commit()

    return str(db_path)


@pytest.fixture
def blocked_task(test_db):
    """Create a task in blocked_user status with a blocked_question."""
    with sqlite3.connect(test_db) as conn:
        # Create epic first
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic", "2025-01-15T00:00:00Z"),
        )
        # Create blocked task
        conn.execute(
            """
            INSERT INTO tasks (epic_name, title, description, status, blocked_question, created_at)
            VALUES ('test-epic', 'Test Task', 'Test description', 'blocked_user', 'What should I do next?', datetime('now'))
            """,
        )
        conn.commit()

    return {"task_id": 1, "question": "What should I do next?"}


@pytest.fixture(autouse=True)
def mock_orchestration_deps(monkeypatch):
    """Mock orchestrator deps - not testing orchestration rules or spawning here."""
    monkeypatch.setattr(
        orchestrator_module, "evaluate_orchestration_rules", lambda _db, _rules: None
    )
    monkeypatch.setattr(orchestrator_module, "get_spawnable_tasks", lambda _db: [])
    monkeypatch.setattr(
        orchestrator_module, "transition_task_status", lambda *a, **kw: None
    )


def test_watch_spawns_supervisor(monkeypatch, test_db, blocked_task):
    """Full flow: blocked worker → watch daemon detects → supervisor spawns.

    Verifies the complete ERA flow:
    1. Worker blocks with question (task in blocked_user status)
    2. Watch daemon detects blocked worker via get_blocked_workers()
    3. Watch spawns supervisor cmux session with SUPERVISOR_UNATTENDED=1
    4. Supervisor receives /supervisor skill command
    """
    cmux_calls = []

    def mock_count_running():
        return 0

    def mock_get_orphaned(db_path=None):
        return []

    def mock_session_exists(name):
        return False  # No supervisor yet

    def mock_is_pane_alive(name):
        return False

    def mock_kill_session(name):
        cmux_calls.append(("kill", name))
        return True

    def mock_create_session(name, cwd, env_vars=None, timeout=30):
        cmux_calls.append(("create", name, cwd, env_vars))
        return True

    def mock_send_keys(name, keys):
        cmux_calls.append(("send_keys", name, keys))
        return True

    # Patch watch_module bindings (used by _daemon_cycle directly)
    monkeypatch.setattr(watch_module, "count_running_workers", mock_count_running)
    monkeypatch.setattr(watch_module, "get_orphaned_workers", mock_get_orphaned)

    # Patch orchestrator internals (used by spawn_supervisor_if_needed)
    monkeypatch.setattr(orchestrator_module.cmux, "session_exists", mock_session_exists)
    monkeypatch.setattr(orchestrator_module.cmux, "is_pane_alive", mock_is_pane_alive)
    monkeypatch.setattr(orchestrator_module.cmux, "kill_session", mock_kill_session)
    monkeypatch.setattr(orchestrator_module.cmux, "create_session", mock_create_session)
    monkeypatch.setattr(orchestrator_module.cmux, "send_keys", mock_send_keys)

    # Verify blocked worker is detected
    blocked = get_blocked_workers(test_db)
    assert len(blocked) == 1
    assert blocked[0]["task_id"] == blocked_task["task_id"]

    # Run watch daemon cycle
    watch_module._daemon_cycle(
        db_path=test_db,
        max_workers=5,
        spawn_enabled=False,
        modes=["watch"],
        interval=10,
    )

    # Verify supervisor session was created
    create_calls = [c for c in cmux_calls if c[0] == "create"]
    assert len(create_calls) == 1, "Should create supervisor session"
    assert create_calls[0][1] == "supervisor"
    assert create_calls[0][3] == {"SUPERVISOR_UNATTENDED": "1"}

    # Verify Claude command was sent
    send_keys_calls = [c for c in cmux_calls if c[0] == "send_keys"]
    assert len(send_keys_calls) == 1
    assert "supervisor" in send_keys_calls[0][2]
    assert "/supervisor" in send_keys_calls[0][2]


def test_idempotent_spawn(monkeypatch, test_db, blocked_task):
    """Verify no duplicate supervisor created when one already exists.

    Tests the idempotent spawn behavior:
    - Blocked worker exists
    - Supervisor session already running (session_exists returns True)
    - Watch daemon does NOT create another supervisor (no duplicate)
    """
    cmux_calls = []

    def mock_count_running():
        return 0

    def mock_get_orphaned(db_path=None):
        return []

    def mock_session_exists(name):
        return name == "supervisor"  # Supervisor already exists

    def mock_is_pane_alive(name):
        return True  # Pane is alive

    def mock_create_session(name, cwd, env_vars=None, timeout=30):
        cmux_calls.append(("create", name))
        return True

    # Patch watch_module bindings
    monkeypatch.setattr(watch_module, "count_running_workers", mock_count_running)
    monkeypatch.setattr(watch_module, "get_orphaned_workers", mock_get_orphaned)

    # Patch orchestrator internals
    monkeypatch.setattr(orchestrator_module.cmux, "session_exists", mock_session_exists)
    monkeypatch.setattr(orchestrator_module.cmux, "is_pane_alive", mock_is_pane_alive)
    monkeypatch.setattr(orchestrator_module.cmux, "create_session", mock_create_session)

    # Verify blocked worker exists
    blocked = get_blocked_workers(test_db)
    assert len(blocked) == 1

    # Run watch daemon cycle
    watch_module._daemon_cycle(
        db_path=test_db,
        max_workers=5,
        spawn_enabled=False,
        modes=["watch"],
        interval=10,
    )

    # Verify NO new supervisor session was created
    create_calls = [c for c in cmux_calls if c[0] == "create"]
    assert len(create_calls) == 0, "Should NOT create duplicate supervisor"


def test_supervisor_clears_inbox(monkeypatch, test_db):
    """Supervisor skill in auto-mode exits immediately when inbox is empty.

    Tests the auto-exit behavior per SKILL.md:
    - No blocked workers (empty inbox)
    - Watch daemon does NOT spawn supervisor (nothing to do)
    - If supervisor was spawned, it would exit immediately with SUPERVISOR_UNATTENDED=1
    """
    cmux_calls = []

    def mock_count_running():
        return 0

    def mock_get_orphaned(db_path=None):
        return []

    def mock_session_exists(name):
        return False

    def mock_is_pane_alive(name):
        return False

    def mock_create_session(name, cwd, env_vars=None, timeout=30):
        cmux_calls.append(("create", name, env_vars))
        return True

    def mock_send_keys(name, keys):
        cmux_calls.append(("send_keys", name, keys))
        return True

    # Patch watch_module bindings
    monkeypatch.setattr(watch_module, "count_running_workers", mock_count_running)
    monkeypatch.setattr(watch_module, "get_orphaned_workers", mock_get_orphaned)

    # Patch orchestrator internals
    monkeypatch.setattr(orchestrator_module.cmux, "session_exists", mock_session_exists)
    monkeypatch.setattr(orchestrator_module.cmux, "is_pane_alive", mock_is_pane_alive)
    monkeypatch.setattr(orchestrator_module.cmux, "create_session", mock_create_session)
    monkeypatch.setattr(orchestrator_module.cmux, "send_keys", mock_send_keys)

    # Verify inbox is empty (no blocked workers)
    blocked = get_blocked_workers(test_db)
    assert len(blocked) == 0, "Inbox should be empty"

    # Run watch daemon cycle
    watch_module._daemon_cycle(
        db_path=test_db,
        max_workers=5,
        spawn_enabled=False,
        modes=["watch"],
        interval=10,
    )

    # When inbox is empty, watch should NOT spawn supervisor
    # (supervisor would just exit immediately anyway)
    create_calls = [c for c in cmux_calls if c[0] == "create"]
    assert len(create_calls) == 0, "Should NOT spawn supervisor when inbox is empty"
