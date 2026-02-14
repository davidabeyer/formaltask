"""Tests for session functions - worktree session tracking (Task #2627).

Refactored from SessionManager class to standalone functions.
"""


def test_get_current_task_returns_none_for_unknown_worktree(db_path):
    """Should return None when worktree has no session."""
    from formaltask.state.session import get_current_task

    result = get_current_task(db_path, "/unknown/worktree")
    assert result is None


def test_set_current_task_creates_session(db_with_epic_and_tasks):
    """Should create a work session for worktree."""
    from formaltask.state.session import get_current_task, set_current_task

    db_path = db_with_epic_and_tasks

    # Task 1 is open (from fixture)
    set_current_task(db_path, "/test/worktree", 1)

    result = get_current_task(db_path, "/test/worktree")
    assert result == 1


def test_set_current_task_updates_existing_session(db_with_epic_and_tasks):
    """Should update existing session when called twice for same worktree (upsert)."""
    from formaltask.state.session import get_current_task, set_current_task

    db_path = db_with_epic_and_tasks

    # Set task 1 first
    set_current_task(db_path, "/test/worktree", 1)
    assert get_current_task(db_path, "/test/worktree") == 1

    # Update to task 2 (both are open in fixture)
    set_current_task(db_path, "/test/worktree", 2)
    result = get_current_task(db_path, "/test/worktree")

    # Should be updated to task 2, not duplicated
    assert result == 2
