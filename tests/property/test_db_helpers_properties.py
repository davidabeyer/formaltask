"""Property-based tests for db_helpers module."""

import sqlite3

from hypothesis import given, settings
from hypothesis import strategies as st

from formaltask.db.helpers import ensure_task_exists


class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    def test_ensure_task_roundtrip(self):
        """Task validation returns consistent results for created tasks."""

        @given(st.integers(min_value=1, max_value=10000))
        @settings(max_examples=25)
        def check_roundtrip(task_id):
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT)")
            cursor.execute("INSERT INTO tasks VALUES (?, ?)", (task_id, f"Task {task_id}"))

            result = ensure_task_exists(cursor, task_id)

            assert result["id"] == task_id
            assert result["title"] == f"Task {task_id}"
            conn.close()

        check_roundtrip()
