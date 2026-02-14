"""Tests for TaskList widget.

Task #2906: row_marker, safety_promote, NEW tag lifecycle, change counter.
"""

from __future__ import annotations

from typing import Any

from formaltask.apps.dashboard.widgets.task_row import TaskRow

# --- AC c-2: row_marker values ---


def test_state_to_row_data_markers() -> None:
    """row_marker='!' for error, '?' for blocked_question, ' ' default."""
    from formaltask.apps.dashboard.widgets.task_list import TaskList

    tl = TaskList()

    # Error status -> '!'
    state = {"health_state": "blocked", "tmux_session_exists": True, "title": "t"}
    assert tl._state_to_row_data(1, state).row_marker == "!"

    # Zombie (tmux gone, health running) -> '!'
    state = {"health_state": "implementing", "tmux_session_exists": False, "title": "t"}
    assert tl._state_to_row_data(2, state).row_marker == "!"

    # Blocked question -> '?'
    state = {
        "health_state": "implementing",
        "tmux_session_exists": True,
        "title": "t",
        "pending_question": "Which approach?",
    }
    assert tl._state_to_row_data(3, state).row_marker == "?"

    # Normal -> ' '
    state = {"health_state": "implementing", "tmux_session_exists": True, "title": "t"}
    assert tl._state_to_row_data(4, state).row_marker == " "


# --- AC c-3: safety promote ---


def test_safety_promote_exit_help() -> None:
    """EXIT/HELP phase rows promoted above queued even without keypress."""
    from formaltask.apps.dashboard.widgets.task_list import TaskList

    tl = TaskList()
    mounted: list = []
    tl.mount = lambda w: mounted.append(w)
    tl.query = lambda _cls: []

    states: dict[int, dict[str, Any]] = {
        10: {
            "task_id": 10,
            "title": "Running",
            "health_state": "implementing",
            "tmux_session_exists": True,
        },
        20: {
            "task_id": 20,
            "title": "Exited",
            "health_state": "exited",
            "tmux_session_exists": False,
        },
        30: {
            "task_id": 30,
            "title": "Help",
            "health_state": "needs_human",
            "tmux_session_exists": True,
        },
    }
    spawnable = [{"id": 40, "title": "Q1"}, {"id": 50, "title": "Q2"}]

    tl.refresh_from_states(
        states, selected_id=None, spawnable_ids=[40, 50], spawnable_tasks=spawnable
    )

    task_ids = [w.data.task_id for w in mounted if isinstance(w, TaskRow)]

    # Find where queued tasks start
    queued_start = next(i for i, tid in enumerate(task_ids) if tid in (40, 50))

    # EXIT(20) and HELP(30) must be before queued tasks
    assert task_ids.index(20) < queued_start
    assert task_ids.index(30) < queued_start

    # Queue separator should exist
    separators = [w for w in mounted if not isinstance(w, TaskRow)]
    assert len(separators) >= 1


# --- AC c-4: NEW tag lifecycle ---


def test_new_tag_lifecycle() -> None:
    """is_new=True on state change, cleared when cursor visits row."""
    from formaltask.apps.dashboard.widgets.task_list import TaskList

    tl = TaskList()
    tl.mount = lambda w: None
    tl.query = lambda _cls: []

    states: dict[int, dict[str, Any]] = {
        42: {
            "task_id": 42,
            "title": "Task",
            "health_state": "implementing",
            "tmux_session_exists": True,
        }
    }

    # First refresh: baseline
    tl.refresh_from_states(states, selected_id=None)
    assert tl._row_cache[42].data.is_new is False, "First appearance not NEW"

    # Phase changes -> NEW
    states[42]["health_state"] = "needs_fix"
    tl.refresh_from_states(states, selected_id=None)
    assert tl._row_cache[42].data.is_new is True, "State change sets NEW"

    # Cursor visits -> clears NEW
    tl.update_selection(42)
    assert tl._row_cache[42].data.is_new is False, "Cursor visit clears NEW"


# --- B1: kill_task eager removal ---


def test_kill_task_removes_row_immediately() -> None:
    """kill_task() adds to _killed_task_ids, removes from _row_cache."""
    from unittest.mock import MagicMock

    from formaltask.apps.dashboard.widgets.task_list import TaskList

    tl = TaskList()
    tl.mount = lambda w: None
    tl.query = lambda _cls: []

    # Seed a row via refresh
    states: dict[int, dict] = {
        42: {
            "task_id": 42,
            "title": "Task",
            "health_state": "implementing",
            "tmux_session_exists": True,
        }
    }
    tl.refresh_from_states(states, selected_id=None)
    assert 42 in tl._row_cache

    # Mock row.remove() since we're not in a real DOM
    row = tl._row_cache[42]
    row.remove = MagicMock()

    tl.kill_task(42)

    assert 42 not in tl._row_cache
    assert 42 in tl._killed_task_ids
    row.remove.assert_called_once()


def test_killed_ids_cleared_after_poll_confirms() -> None:
    """_killed_task_ids entry cleared when refresh_from_states confirms task absent."""
    from formaltask.apps.dashboard.widgets.task_list import TaskList

    tl = TaskList()
    tl.mount = lambda w: None
    tl.query = lambda _cls: []

    # Seed _killed_task_ids directly
    tl._killed_task_ids = {42}

    # Refresh with no states — task 42 is confirmed gone
    tl.refresh_from_states({}, selected_id=None)

    assert 42 not in tl._killed_task_ids, "killed_id should be cleared after poll confirms absence"


def test_killed_ids_suppress_row_creation() -> None:
    """Rows for killed task_ids are not re-created even if states still contain them."""
    from formaltask.apps.dashboard.widgets.task_list import TaskList

    tl = TaskList()
    mounted = []
    tl.mount = lambda w: mounted.append(w)
    tl.query = lambda _cls: []

    # Pre-kill task 42
    tl._killed_task_ids = {42}

    states: dict[int, dict] = {
        42: {
            "task_id": 42,
            "title": "Ghost",
            "health_state": "implementing",
            "tmux_session_exists": True,
        }
    }
    tl.refresh_from_states(states, selected_id=None)

    # Task 42 should NOT be in row_cache (suppressed by killed_ids)
    assert 42 not in tl._row_cache


