"""Tests for post-commit hook - check_task_completion.py

Tests warning message when tasks are incomplete after commit.
"""

import sys
from pathlib import Path

# Add post-commit directory to path for check_task_completion import
_THIS_DIR = Path(__file__).parent
sys.path.insert(0, str(_THIS_DIR))


def test_warns_when_task_incomplete(tmp_path, capsys):
    """Test that post-commit hook warns when task is started but not completed."""
    import os

    import check_task_completion

    from formaltask.db.schema import ensure_schema_initialized
    from formaltask.tasks.crud import create_task
    from formaltask.tasks.lifecycle import transition_task_status

    # Given: A database with started but not completed task
    db_path = str(tmp_path / "test.db")
    ensure_schema_initialized(db_path)
    # Note: ensure_schema_initialized creates master-adhoc epic automatically

    # Create and start a task
    task_id = create_task(db_path, "master-adhoc", "Test task", "Description", ["Criterion 1"])
    transition_task_status(db_path, task_id, "in_progress")

    # Set environment variable to point to test database
    os.environ["FORMALTASK_DB_PATH"] = str(db_path)

    try:
        # When: Running post-commit hook check
        check_task_completion.check_incomplete_tasks()

        # Then: Warning should be printed
        captured = capsys.readouterr()
        assert "incomplete" in captured.out.lower() or "in-progress" in captured.out.lower(), (
            "Should warn about incomplete tasks"
        )
        assert str(task_id) in captured.out, "Should mention task ID"
        assert "/pm-task-complete" in captured.out, "Should suggest completion command"

    finally:
        # Clean up environment
        os.environ.pop("FORMALTASK_DB_PATH", None)
