"""Tests for review_status column deprecation (Task #2013).

Verifies the review_status column is properly removed from the tasks table.
"""

import sqlite3


class TestReviewStatusColumnRemoved:
    """Tests that review_status column is properly removed."""

    def test_review_status_column_not_in_tasks_table(self, db_path):
        """Verify review_status column does not exist in tasks table."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(tasks)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        assert "review_status" not in columns, (
            "review_status column should be removed from tasks table"
        )

    def test_review_status_index_not_exists(self, db_path):
        """Verify idx_tasks_review_status index is removed."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_tasks_review_status'"
        )
        result = cursor.fetchone()
        conn.close()

        assert result is None, "idx_tasks_review_status index should be removed"

    def test_get_task_does_not_include_review_status(self, db_path, repo):
        """Verify get_task() result does not contain review_status key."""
        from formaltask.tasks.crud import get_task

        repo.create_epic("test-epic", "Test epic")
        task_id = repo.create_task(
            epic_name="test-epic",
            title="Test task",
            description="Test description",
            criteria=["Criterion 1"],
        )

        task = get_task(db_path, task_id)

        assert task is not None, "Task should exist"
        assert "review_status" not in task, "review_status should not be in get_task() result"
