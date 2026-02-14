"""Property-based tests for task_status_checker module.

Tests edge cases and invariants for branch name parsing and merge logic
via the check_merge_allowed() public API.
"""

import sqlite3

from hypothesis import given, settings
from hypothesis import strategies as st

from formaltask.tasks.status import check_merge_allowed


def _create_test_db(tmp_path, task_id, status="completed"):
    """Create a test database with a single task."""
    db_file = tmp_path / "formaltask.db"
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'open'
            )
        """)
        cursor.execute("INSERT INTO tasks (id, status) VALUES (?, ?)", (task_id, status))
        conn.commit()
    return str(db_file)


@given(task_id=st.integers(min_value=1, max_value=999999999))
@settings(max_examples=100, deadline=None)
def test_extract_task_id_roundtrip(task_id, tmp_path_factory):
    """Property: task-{id}-suffix always extracts to id."""
    tmp_path = tmp_path_factory.mktemp("db")
    db_path = _create_test_db(tmp_path, task_id)
    branch = f"task-{task_id}-feature"
    result = check_merge_allowed(branch, db_path)
    assert result["task_id"] == task_id


@given(task_id=st.integers(min_value=1, max_value=999999999))
@settings(max_examples=100, deadline=None)
def test_extract_task_id_slash_separator(task_id, tmp_path_factory):
    """Property: task/{id}/suffix always extracts to id."""
    tmp_path = tmp_path_factory.mktemp("db")
    db_path = _create_test_db(tmp_path, task_id)
    branch = f"task/{task_id}/feature"
    result = check_merge_allowed(branch, db_path)
    assert result["task_id"] == task_id


@given(
    branch=st.text(min_size=0, max_size=100).filter(
        lambda s: "task-" not in s.lower() and "task/" not in s.lower()
    )
)
@settings(max_examples=100, deadline=None)
def test_non_task_branch_returns_none(branch, tmp_path_factory):
    """Property: Branches without task pattern return None."""
    tmp_path = tmp_path_factory.mktemp("db")
    db_path = _create_test_db(tmp_path, 1)  # Create db with any task
    result = check_merge_allowed(branch, db_path)
    assert result["task_id"] is None


@given(
    task_id=st.integers(min_value=1, max_value=999999),
    case_pattern=st.sampled_from(["task", "TASK", "Task", "TaSk", "tAsK"]),
)
@settings(max_examples=50, deadline=None)
def test_extract_task_id_case_insensitive(task_id, case_pattern, tmp_path_factory):
    """Property: Task pattern is case-insensitive."""
    tmp_path = tmp_path_factory.mktemp("db")
    db_path = _create_test_db(tmp_path, task_id)
    branch = f"{case_pattern}-{task_id}-feature"
    result = check_merge_allowed(branch, db_path)
    assert result["task_id"] == task_id
