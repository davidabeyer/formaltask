"""Test semantic equivalence between SQL views and Python logic.

Task #2750: Verify task_ready_status view matches get_spawnable_tasks() behavior.
The SQL view must treat cancelled tasks as satisfying dependencies (like Python does).
"""

import sqlite3

from formaltask.tasks.spawnability import get_spawnable_tasks


def test_view_matches_python_for_cancelled_dependency(db_path: str):
    """Task with cancelled dependency appears in view AND Python output.

    Setup:
        - Task A (cancelled)
        - Task B depends on Task A

    Expected: B appears in both task_ready_status view and get_spawnable_tasks()

    This tests AC1 (cancelled tasks satisfy dependencies) and AC2 (semantic equivalence).
    """
    with sqlite3.connect(db_path) as conn:
        # Create epic
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("equiv-test", "Equivalence test epic", "2025-01-01T00:00:00Z"),
        )

        # Task A - will be cancelled
        conn.execute(
            """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (100, "equiv-test", "Task A", "Dependency task", "cancelled", "2025-01-01T00:00:00Z"),
        )

        # Task B - depends on Task A
        conn.execute(
            """INSERT INTO tasks (id, epic_name, title, description, status, depends_on, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                101,
                "equiv-test",
                "Task B",
                "Dependent task",
                "open",
                "[100]",
                "2025-01-01T00:00:00Z",
            ),
        )
        conn.commit()

        # Query SQL view
        cursor = conn.cursor()
        cursor.execute("SELECT task_id FROM task_ready_status WHERE task_id = 101")
        view_result = cursor.fetchone()

    # Query Python logic
    python_result = get_spawnable_tasks(db_path)

    # Both should include Task B (101)
    assert view_result is not None, "SQL view should include task with cancelled dependency"
    assert 101 in python_result, "Python should include task with cancelled dependency"


def test_view_excludes_task_with_open_dependency(db_path: str):
    """Task with open (not completed/cancelled) dependency is excluded from both.

    This is a regression test to ensure fixing cancelled doesn't break the basic case.
    """
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("regression-test", "Regression test epic", "2025-01-01T00:00:00Z"),
        )

        # Task A - still open (blocking)
        conn.execute(
            """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (200, "regression-test", "Task A", "Blocking task", "open", "2025-01-01T00:00:00Z"),
        )

        # Task B - depends on Task A
        conn.execute(
            """INSERT INTO tasks (id, epic_name, title, description, status, depends_on, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                201,
                "regression-test",
                "Task B",
                "Blocked task",
                "open",
                "[200]",
                "2025-01-01T00:00:00Z",
            ),
        )
        conn.commit()

        cursor = conn.cursor()
        cursor.execute("SELECT task_id FROM task_ready_status WHERE task_id = 201")
        view_result = cursor.fetchone()

    python_result = get_spawnable_tasks(db_path)

    # Neither should include Task B (blocked by open Task A)
    assert view_result is None, "SQL view should NOT include task blocked by open dependency"
    assert 201 not in python_result, "Python should NOT include task blocked by open dependency"


def test_view_includes_task_with_completed_dependency(db_path: str):
    """Task with completed dependency is included in both (baseline test)."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("baseline-test", "Baseline test epic", "2025-01-01T00:00:00Z"),
        )

        # Task A - completed
        conn.execute(
            """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (300, "baseline-test", "Task A", "Completed task", "completed", "2025-01-01T00:00:00Z"),
        )

        # Task B - depends on Task A
        conn.execute(
            """INSERT INTO tasks (id, epic_name, title, description, status, depends_on, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (301, "baseline-test", "Task B", "Ready task", "open", "[300]", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

        cursor = conn.cursor()
        cursor.execute("SELECT task_id FROM task_ready_status WHERE task_id = 301")
        view_result = cursor.fetchone()

    python_result = get_spawnable_tasks(db_path)

    # Both should include Task B (dependency completed)
    assert view_result is not None, "SQL view should include task with completed dependency"
    assert 301 in python_result, "Python should include task with completed dependency"
