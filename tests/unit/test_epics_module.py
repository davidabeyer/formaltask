"""Tests for formaltask/epics.py module (Task #2723).

TDD approach: Test standalone epic functions with db_path as first param.
"""

import sqlite3

# --- get_epic tests ---


def test_get_epic_returns_none_for_nonexistent(db_path):
    """get_epic returns None when epic doesn't exist."""
    from formaltask.epics import get_epic

    result = get_epic(db_path, "nonexistent")
    assert result is None


def test_get_epic_returns_epic_data(db_path):
    """get_epic returns EpicData dict for existing epic."""
    from formaltask.epics import get_epic

    # Insert epic directly
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, skip_review, created_at) VALUES (?, ?, ?, ?)",
            ("test-epic", "Test description", 0, "2025-01-01T00:00:00Z"),
        )

    result = get_epic(db_path, "test-epic")

    assert result is not None
    assert result["name"] == "test-epic"
    assert result["description"] == "Test description"
    assert result["skip_review"] == 0
    assert result["created_at"] == "2025-01-01T00:00:00Z"
    assert result["archived_at"] is None


# --- create_epic tests ---


def test_create_epic_stores_in_db(db_path):
    """create_epic stores epic in database."""
    from formaltask.epics import create_epic, get_epic

    create_epic(db_path, "new-epic", "New description")

    result = get_epic(db_path, "new-epic")
    assert result is not None
    assert result["name"] == "new-epic"
    assert result["description"] == "New description"
    assert result["skip_review"] == 0


def test_create_epic_with_skip_review_true(db_path):
    """create_epic with skip_review=True stores the flag."""
    from formaltask.epics import create_epic, get_epic

    create_epic(db_path, "skip-review-epic", "Description", skip_review=True)

    result = get_epic(db_path, "skip-review-epic")
    assert result is not None
    assert result["skip_review"] == 1


def test_create_epic_raises_on_duplicate(db_path):
    """create_epic raises IntegrityError on duplicate name."""
    import pytest

    from formaltask.epics import create_epic

    create_epic(db_path, "duplicate-epic", "First")

    with pytest.raises(sqlite3.IntegrityError):
        create_epic(db_path, "duplicate-epic", "Second")


# --- update_epic tests ---


def test_update_epic_changes_description(db_path):
    """update_epic updates epic description."""
    from formaltask.epics import create_epic, get_epic, update_epic

    create_epic(db_path, "update-test", "Old description")
    update_epic(db_path, "update-test", "New description")

    result = get_epic(db_path, "update-test")
    assert result["description"] == "New description"


def test_update_epic_raises_for_nonexistent(db_path):
    """update_epic raises ValueError for nonexistent epic."""
    import pytest

    from formaltask.epics import update_epic

    with pytest.raises(ValueError, match="not found"):
        update_epic(db_path, "nonexistent", "Description")


# --- archive_epic tests ---


def test_archive_epic_sets_archived_at(db_path):
    """archive_epic sets archived_at timestamp."""
    from formaltask.epics import archive_epic, create_epic, get_epic

    create_epic(db_path, "archive-test", "Description")
    archive_epic(db_path, "archive-test", force=True)

    result = get_epic(db_path, "archive-test")
    assert result["archived_at"] is not None


def test_archive_epic_raises_for_nonexistent(db_path):
    """archive_epic raises ValueError for nonexistent epic."""
    import pytest

    from formaltask.epics import archive_epic

    with pytest.raises(ValueError, match="not found"):
        archive_epic(db_path, "nonexistent")


def test_archive_epic_raises_with_incomplete_tasks(db_path):
    """archive_epic raises ValueError when epic has incomplete tasks (force=False)."""
    import pytest

    from formaltask.epics import archive_epic, create_epic

    create_epic(db_path, "incomplete-epic", "Description")
    # Add an open task
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO tasks (epic_name, title, description, status, created_at) VALUES (?, ?, ?, ?, ?)",
            ("incomplete-epic", "Open task", "Desc", "open", "2025-01-01T00:00:00Z"),
        )

    with pytest.raises(ValueError, match="incomplete tasks"):
        archive_epic(db_path, "incomplete-epic", force=False)


def test_archive_epic_force_false_no_incomplete_tasks(db_path):
    """archive_epic succeeds with force=False when no incomplete tasks."""
    from formaltask.epics import archive_epic, create_epic, get_epic

    create_epic(db_path, "complete-epic", "Description")
    # Add only completed tasks
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO tasks (epic_name, title, description, status, created_at) VALUES (?, ?, ?, ?, ?)",
            ("complete-epic", "Done task", "Desc", "completed", "2025-01-01T00:00:00Z"),
        )

    archive_epic(db_path, "complete-epic", force=False)

    result = get_epic(db_path, "complete-epic")
    assert result["archived_at"] is not None


def test_archive_epic_already_archived_is_idempotent(db_path):
    """archive_epic on already-archived epic is a no-op."""
    from formaltask.epics import archive_epic, create_epic, get_epic

    create_epic(db_path, "double-archive", "Description")
    archive_epic(db_path, "double-archive", force=True)

    first_archived_at = get_epic(db_path, "double-archive")["archived_at"]

    # Archive again - should not raise, should not change timestamp
    archive_epic(db_path, "double-archive", force=True)

    second_archived_at = get_epic(db_path, "double-archive")["archived_at"]
    assert first_archived_at == second_archived_at


# --- unarchive_epic tests ---


def test_unarchive_epic_clears_archived_at(db_path):
    """unarchive_epic clears archived_at timestamp."""
    from formaltask.epics import archive_epic, create_epic, get_epic, unarchive_epic

    create_epic(db_path, "unarchive-test", "Description")
    archive_epic(db_path, "unarchive-test", force=True)
    unarchive_epic(db_path, "unarchive-test")

    result = get_epic(db_path, "unarchive-test")
    assert result["archived_at"] is None


def test_unarchive_epic_raises_for_nonexistent(db_path):
    """unarchive_epic raises ValueError for nonexistent epic."""
    import pytest

    from formaltask.epics import unarchive_epic

    with pytest.raises(ValueError, match="not found"):
        unarchive_epic(db_path, "nonexistent")


def test_unarchive_epic_not_archived_is_idempotent(db_path):
    """unarchive_epic on non-archived epic is a no-op."""
    from formaltask.epics import create_epic, get_epic, unarchive_epic

    create_epic(db_path, "never-archived", "Description")

    # Unarchive an epic that was never archived - should not raise
    unarchive_epic(db_path, "never-archived")

    result = get_epic(db_path, "never-archived")
    assert result["archived_at"] is None


# --- get_epic_status tests ---


def test_get_epic_status_returns_counts(db_path):
    """get_epic_status returns task counts from VIEW."""
    from formaltask.epics import create_epic, get_epic_status

    create_epic(db_path, "status-test", "Description")
    # Add tasks
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO tasks (epic_name, title, description, status, created_at) VALUES (?, ?, ?, ?, ?)",
            ("status-test", "Task 1", "Desc", "open", "2025-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO tasks (epic_name, title, description, status, created_at) VALUES (?, ?, ?, ?, ?)",
            ("status-test", "Task 2", "Desc", "completed", "2025-01-01T00:00:00Z"),
        )

    result = get_epic_status(db_path, "status-test")
    assert result["name"] == "status-test"
    assert result["total_tasks"] == 2
    assert result["completed"] == 1


def test_get_epic_status_returns_none_for_nonexistent(db_path):
    """get_epic_status returns None for nonexistent epic."""
    from formaltask.epics import get_epic_status

    result = get_epic_status(db_path, "nonexistent")
    assert result is None


# --- mark_reviewed tests ---


def test_mark_reviewed_sets_timestamp(db_path):
    """mark_reviewed sets reviewed_at timestamp."""
    from formaltask.epics import create_epic, mark_reviewed

    create_epic(db_path, "review-test", "Description")
    mark_reviewed(db_path, "review-test")

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT reviewed_at FROM epics WHERE name = ?", ("review-test",))
        reviewed_at = cursor.fetchone()[0]

    assert reviewed_at is not None


def test_mark_reviewed_raises_for_nonexistent(db_path):
    """mark_reviewed raises ValueError for nonexistent epic."""
    import pytest

    from formaltask.epics import mark_reviewed

    with pytest.raises(ValueError, match="not found"):
        mark_reviewed(db_path, "nonexistent")


def test_mark_reviewed_raises_for_archived(db_path):
    """mark_reviewed raises ValueError for archived epic."""
    import pytest

    from formaltask.epics import archive_epic, create_epic, mark_reviewed

    create_epic(db_path, "archived-review", "Description")
    archive_epic(db_path, "archived-review", force=True)

    with pytest.raises(ValueError, match="archived"):
        mark_reviewed(db_path, "archived-review")


# --- list_epics tests ---


def test_list_epics_returns_all_epics(db_path):
    """list_epics returns all epics."""
    from formaltask.epics import create_epic, list_epics

    create_epic(db_path, "epic-1", "Description 1")
    create_epic(db_path, "epic-2", "Description 2")

    result = list_epics(db_path)
    names = [e["name"] for e in result]

    assert "epic-1" in names
    assert "epic-2" in names


def test_list_epics_returns_empty_when_none(db_path):
    """list_epics returns empty list when no epics exist."""
    from formaltask.epics import list_epics

    # Delete any default epics
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM epics")

    result = list_epics(db_path)
    assert result == []
