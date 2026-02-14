"""Tests for get_spawnable_tasks() - task spawnability logic.

Task #2725: Converted from class-based tests to function-based tests.
"""


def test_get_spawnable_tasks_returns_open_tasks(db_with_epic_and_tasks):
    """Should return open tasks with completed dependencies."""
    from formaltask.tasks.spawnability import get_spawnable_tasks

    db_path = db_with_epic_and_tasks

    # Fixture has tasks 1,2 open, 3 in_progress, 4 completed, 5 blocked
    # Tasks 1,2 should be spawnable (open, no dependencies)
    result = get_spawnable_tasks(db_path)
    assert isinstance(result, list)
    assert 1 in result
    assert 2 in result


def test_get_spawnable_tasks_excludes_tasks_with_unmet_deps(db_with_epic_and_tasks):
    """Task with unmet dependencies should not be spawnable."""
    import json
    import sqlite3

    from formaltask.tasks.spawnability import get_spawnable_tasks

    db_path = db_with_epic_and_tasks

    # Add dependency: task 1 depends on task 3 (which is in_progress)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE tasks SET depends_on = ? WHERE id = 1", (json.dumps([3]),))

    result = get_spawnable_tasks(db_path)

    # Task 1 should NOT be spawnable (depends on in_progress task 3)
    assert 1 not in result
    # Task 2 should still be spawnable (no dependencies)
    assert 2 in result


def test_get_spawnable_tasks_excludes_archived_epic_tasks(db_with_epic_and_tasks):
    """Tasks in archived epics should NOT appear in spawnable list."""
    import sqlite3
    from datetime import datetime

    from formaltask.tasks.spawnability import get_spawnable_tasks

    db_path = db_with_epic_and_tasks

    # Archive the epic containing our tasks
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE epics SET archived_at = ? WHERE name = 'test-epic'",
            (datetime.now().isoformat(),),
        )

    result = get_spawnable_tasks(db_path)

    # No tasks should be spawnable since the epic is archived
    assert 1 not in result
    assert 2 not in result
    assert result == []


def test_get_spawnable_tasks_handles_invalid_json_gracefully(db_with_epic_and_tasks, caplog):
    """Invalid JSON in depends_on should be logged and treated as empty."""
    import logging
    import sqlite3

    from formaltask.tasks.spawnability import get_spawnable_tasks

    db_path = db_with_epic_and_tasks

    # Set invalid JSON in depends_on field
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE tasks SET depends_on = '{invalid json' WHERE id = 1")

    with caplog.at_level(logging.WARNING):
        result = get_spawnable_tasks(db_path)

    # Task 1 should still be spawnable (invalid JSON treated as no deps)
    assert 1 in result
    # Warning should be logged (uses shared parse_depends_on from db_helpers)
    assert "malformed depends_on JSON" in caplog.text


# ============================================================================
# File Overlap Blocking Tests (Task #2275)
# ============================================================================


def _make_spec_metadata(spec_content: str) -> str:
    """Helper to create valid spec metadata JSON."""
    import json

    return json.dumps({"artifact_type": "spec", "artifact_content": spec_content})


def test_get_spawnable_tasks_blocks_file_overlap_with_in_progress(db_with_epic_and_tasks):
    """Task with file overlap against in_progress task should NOT be spawnable."""
    import sqlite3

    from formaltask.tasks.spawnability import get_spawnable_tasks

    db_path = db_with_epic_and_tasks

    # Task 3 is in_progress - give it a spec touching foo.py
    # Task 1 is open - give it a spec also touching foo.py (overlap!)
    # Task 2 is open - give it a spec touching bar.py (no overlap)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET metadata = ? WHERE id = 3",
            (_make_spec_metadata("Modify `foo.py` to add feature"),),
        )
        conn.execute(
            "UPDATE tasks SET metadata = ? WHERE id = 1",
            (_make_spec_metadata("Edit `foo.py` to fix bug"),),  # overlaps with task 3
        )
        conn.execute(
            "UPDATE tasks SET metadata = ? WHERE id = 2",
            (_make_spec_metadata("Create `bar.py` for new module"),),  # no overlap
        )

    result = get_spawnable_tasks(db_path)

    # Task 1 blocked due to file overlap with in_progress task 3
    assert 1 not in result
    # Task 2 spawnable (no overlap)
    assert 2 in result


def test_get_spawnable_tasks_allows_non_overlapping_files(db_with_epic_and_tasks):
    """Tasks touching different files should all be spawnable."""
    import sqlite3

    from formaltask.tasks.spawnability import get_spawnable_tasks

    db_path = db_with_epic_and_tasks

    # Task 3 is in_progress touching foo.py
    # Tasks 1,2 are open touching bar.py and baz.py (no overlap)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET metadata = ? WHERE id = 3",
            (_make_spec_metadata("Modify `foo.py`"),),
        )
        conn.execute(
            "UPDATE tasks SET metadata = ? WHERE id = 1",
            (_make_spec_metadata("Modify `bar.py`"),),
        )
        conn.execute(
            "UPDATE tasks SET metadata = ? WHERE id = 2",
            (_make_spec_metadata("Modify `baz.py`"),),
        )

    result = get_spawnable_tasks(db_path)

    # Both tasks spawnable (different files)
    assert 1 in result
    assert 2 in result


def test_get_spawnable_tasks_no_in_progress_allows_all(db_with_epic_and_tasks):
    """When no tasks are in_progress, file overlap check is skipped."""
    import sqlite3

    from formaltask.tasks.spawnability import get_spawnable_tasks

    db_path = db_with_epic_and_tasks

    # Change task 3 from in_progress to completed
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE tasks SET status = 'completed' WHERE id = 3")
        # Give tasks 1,2 same file (would conflict if task 3 was in_progress)
        conn.execute(
            "UPDATE tasks SET metadata = ? WHERE id = 1",
            (_make_spec_metadata("Modify `same.py`"),),
        )
        conn.execute(
            "UPDATE tasks SET metadata = ? WHERE id = 2",
            (_make_spec_metadata("Modify `same.py`"),),
        )

    result = get_spawnable_tasks(db_path)

    # Both spawnable (no in_progress to conflict with)
    assert 1 in result
    assert 2 in result


def test_get_spawnable_tasks_empty_spec_no_overlap(db_with_epic_and_tasks):
    """Tasks without spec content should not be blocked by file overlap."""
    import sqlite3

    from formaltask.tasks.spawnability import get_spawnable_tasks

    db_path = db_with_epic_and_tasks

    # Task 3 in_progress with spec
    # Task 1 open without metadata (should be spawnable)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET metadata = ? WHERE id = 3",
            (_make_spec_metadata("Modify `foo.py`"),),
        )
        conn.execute("UPDATE tasks SET metadata = NULL WHERE id = 1")

    result = get_spawnable_tasks(db_path)

    # Task 1 spawnable (no spec means no file overlap check)
    assert 1 in result


def test_get_spawnable_tasks_path_normalization(db_with_epic_and_tasks):
    """File paths should be normalized for overlap detection."""
    import sqlite3

    from formaltask.tasks.spawnability import get_spawnable_tasks

    db_path = db_with_epic_and_tasks

    # Task 3 in_progress with ./src/foo.py
    # Task 1 open with src/foo.py (same file after normalization)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET metadata = ? WHERE id = 3",
            (_make_spec_metadata("Modify `./src/foo.py`"),),
        )
        conn.execute(
            "UPDATE tasks SET metadata = ? WHERE id = 1",
            (_make_spec_metadata("Edit `src/foo.py`"),),
        )

    result = get_spawnable_tasks(db_path)

    # Task 1 blocked (paths normalize to same file)
    assert 1 not in result
