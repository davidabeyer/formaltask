"""Behavioral tests for WorkerDashboard keybindings.

Tests verify actual keybinding behavior, not just binding registration.
Each test asserts actual behavior changes (screens, reactive properties, UI state).

Uses a lightweight stub instead of MagicMock(spec=WorkerDashboard) to make
attribute access explicit — accessing an unset attribute raises AttributeError
instead of silently returning a MagicMock.
"""

import time
from types import SimpleNamespace
from unittest.mock import Mock

from formaltask.apps.dashboard import WorkerDashboard


def _make_dashboard_stub(**overrides) -> SimpleNamespace:
    """Create a minimal stub with action_kill's required attributes."""
    defaults = {
        "_modal_active": False,
        "selected_task_id": None,
        "_pending_kill": None,
        "notify": Mock(),
        "_handle_kill_confirm": Mock(),
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_x_key_first_press_sets_pending_kill() -> None:
    """First X key press sets pending_kill state for confirmation."""
    stub = _make_dashboard_stub(selected_task_id=42)

    WorkerDashboard.action_kill(stub)

    assert stub._pending_kill is not None
    assert stub._pending_kill[0] == 42
    stub.notify.assert_called_once()
    call_args = stub.notify.call_args
    assert "again to kill" in call_args[0][0]
    assert call_args[1]["severity"] == "warning"


def test_x_key_second_press_executes_kill() -> None:
    """Second X key press within timeout executes kill confirmation."""
    stub = _make_dashboard_stub(
        selected_task_id=42,
        _pending_kill=(42, time.time() - 1.0),
    )

    WorkerDashboard.action_kill(stub)

    stub._handle_kill_confirm.assert_called_once_with(True, 42)
    assert stub._pending_kill is None


def test_x_key_expired_timeout_resets_pending_kill() -> None:
    """Second X press after 3s timeout resets pending state instead of confirming."""
    stub = _make_dashboard_stub(
        selected_task_id=42,
        _pending_kill=(42, time.time() - 4.0),
    )

    WorkerDashboard.action_kill(stub)

    stub._handle_kill_confirm.assert_not_called()
    assert stub._pending_kill is not None
    assert stub._pending_kill[0] == 42


def test_x_key_different_task_resets_pending() -> None:
    """X key on different task resets pending state to new task."""
    stub = _make_dashboard_stub(
        selected_task_id=99,
        _pending_kill=(42, time.time() - 1.0),
    )

    WorkerDashboard.action_kill(stub)

    stub._handle_kill_confirm.assert_not_called()
    assert stub._pending_kill is not None
    assert stub._pending_kill[0] == 99
    stub.notify.assert_called_once()
    assert "task-99" in stub.notify.call_args[0][0]


def test_x_key_no_worker_selected_shows_error() -> None:
    """X key without worker selected shows error notification."""
    stub = _make_dashboard_stub()

    WorkerDashboard.action_kill(stub)

    stub.notify.assert_called_once_with("No worker selected", severity="error")
