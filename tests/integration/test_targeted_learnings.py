"""Integration tests for targeted learnings flow (Task #2675 - VERIFY).

Tests the complete flow: CLI → Storage → SessionStart injection

Test scenario:
    Epic: test-verify-epic
    ├── Task A (in_progress) - stores learning targeting Task B
    ├── Task B (pending) - should receive learning
    └── Task C (pending) - should NOT receive learning
"""

import json
from argparse import Namespace

from formaltask.tasks.lifecycle import transition_task_status


class TestTargetedLearningsIntegration:
    """End-to-end tests for targeted learnings flow."""

    def test_targeted_learning_full_flow_target_receives(self, db_path, repo, monkeypatch):
        """AC: inject_sibling_learnings(task_id=B) returns 'test insight' when A stored --for B.

        Full flow test:
        1. Create epic with 3 tasks (A, B, C)
        2. Store learning from A targeting B via CLI
        3. Complete task A
        4. Verify inject_sibling_learnings(task_id=B) returns the learning
        """
        from formaltask.cli.commands import learning as learning_cmd
        from formaltask.cli.exit_codes import ExitCode
        from hooks.session_start.task_context_loader import inject_sibling_learnings

        # Setup: Create epic with 3 tasks
        repo.create_epic("test-verify-epic", "Verify targeted learnings")
        task_a_id = repo.create_task("test-verify-epic", "Task A", "Source task", ["criterion"])
        task_b_id = repo.create_task("test-verify-epic", "Task B", "Target task", ["criterion"])
        # Task C exists for scenario setup but not accessed in this test
        repo.create_task("test-verify-epic", "Task C", "Non-target task", ["criterion"])

        # Set task A as current context (simulate worker)
        monkeypatch.setenv("TASK_ID", str(task_a_id))

        # Act 1: Store learning from A targeting B via CLI
        args = Namespace(
            learning="test insight",
            targets=str(task_b_id),
            db_path=db_path,
        )
        result = learning_cmd.execute(args)

        assert result == ExitCode.SUCCESS, "CLI should succeed"

        # Act 2: Complete task A (learnings only injected from completed tasks)
        transition_task_status(db_path, task_a_id, "in_progress")
        transition_task_status(db_path, task_a_id, "completed")

        # Assert: inject_sibling_learnings for Task B returns the learning
        result = inject_sibling_learnings(
            task_id=task_b_id,
            epic_name="test-verify-epic",
            db_path=db_path,
        )

        assert result is not None, "Target task B should receive learning"
        assert "test insight" in result, "Learning text should be in result"
        assert f"Task #{task_a_id}" in result, "Should cite source task"

    def test_targeted_learning_non_target_excluded(self, db_path, repo, monkeypatch):
        """AC: inject_sibling_learnings(task_id=C) returns None when A stored --for B.

        Learning stored with --for B should NOT be visible to task C.
        """
        from formaltask.cli.commands import learning as learning_cmd
        from formaltask.cli.exit_codes import ExitCode
        from hooks.session_start.task_context_loader import inject_sibling_learnings

        # Setup: Create epic with 3 tasks
        repo.create_epic("test-verify-epic", "Verify targeted learnings")
        task_a_id = repo.create_task("test-verify-epic", "Task A", "Source task", ["criterion"])
        task_b_id = repo.create_task("test-verify-epic", "Task B", "Target task", ["criterion"])
        task_c_id = repo.create_task("test-verify-epic", "Task C", "Non-target task", ["criterion"])

        # Set task A as current context
        monkeypatch.setenv("TASK_ID", str(task_a_id))

        # Store learning from A targeting B (not C)
        args = Namespace(
            learning="insight for B only",
            targets=str(task_b_id),
            db_path=db_path,
        )
        result = learning_cmd.execute(args)
        assert result == ExitCode.SUCCESS

        # Complete task A
        transition_task_status(db_path, task_a_id, "in_progress")
        transition_task_status(db_path, task_a_id, "completed")

        # Assert: inject_sibling_learnings for Task C returns None
        result = inject_sibling_learnings(
            task_id=task_c_id,
            epic_name="test-verify-epic",
            db_path=db_path,
        )

        assert result is None, "Non-target task C should NOT receive learning"

    def test_old_format_strings_return_none(self, db_path, repo):
        """AC: inject_sibling_learnings() returns None when only old format strings exist.

        Old format: learnings stored as plain strings (no targets field)
        These should be silently skipped.
        """
        import sqlite3

        from hooks.session_start.task_context_loader import inject_sibling_learnings

        # Setup: Create epic with 2 tasks
        repo.create_epic("test-old-format-epic", "Test old format handling")
        task_a_id = repo.create_task(
            "test-old-format-epic", "Task A", "Old format task", ["criterion"]
        )
        task_b_id = repo.create_task(
            "test-old-format-epic", "Task B", "Current task", ["criterion"]
        )

        # Manually insert old format learnings (plain strings, no targets)
        old_format_metadata = json.dumps(
            {"learnings": ["Old format learning 1", "Old format learning 2"]}
        )
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE tasks SET metadata = ?, status = 'completed' WHERE id = ?",
                (old_format_metadata, task_a_id),
            )
            conn.commit()

        # Assert: inject_sibling_learnings returns None (old format skipped)
        result = inject_sibling_learnings(
            task_id=task_b_id,
            epic_name="test-old-format-epic",
            db_path=db_path,
        )

        assert result is None, "Old format strings should be skipped, returning None"

    def test_mixed_format_only_targeted_returned(self, db_path, repo, monkeypatch):
        """Mixed old and new format: only properly targeted learnings returned."""
        import sqlite3

        from formaltask.cli.commands import learning as learning_cmd
        from formaltask.cli.exit_codes import ExitCode
        from hooks.session_start.task_context_loader import inject_sibling_learnings

        # Setup: Create epic with 3 tasks
        repo.create_epic("test-mixed-epic", "Test mixed format handling")
        task_a_id = repo.create_task(
            "test-mixed-epic", "Task A", "Mixed format task", ["criterion"]
        )
        task_b_id = repo.create_task("test-mixed-epic", "Task B", "Target task", ["criterion"])
        task_c_id = repo.create_task("test-mixed-epic", "Task C", "Other task", ["criterion"])

        # First, manually insert old format learning
        old_format_metadata = json.dumps({"learnings": ["Old untargeted learning"]})
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE tasks SET metadata = ? WHERE id = ?",
                (old_format_metadata, task_a_id),
            )
            conn.commit()

        # Now use CLI to add new format learning targeting B
        monkeypatch.setenv("TASK_ID", str(task_a_id))
        args = Namespace(
            learning="New targeted insight",
            targets=str(task_b_id),
            db_path=db_path,
        )
        result = learning_cmd.execute(args)
        assert result == ExitCode.SUCCESS

        # Complete task A
        transition_task_status(db_path, task_a_id, "in_progress")
        transition_task_status(db_path, task_a_id, "completed")

        # Assert: Only the targeted learning is returned for task B
        result = inject_sibling_learnings(
            task_id=task_b_id,
            epic_name="test-mixed-epic",
            db_path=db_path,
        )

        assert result is not None, "Task B should receive targeted learning"
        assert "New targeted insight" in result
        assert "Old untargeted learning" not in result

        # Assert: Task C receives nothing (not targeted)
        result_c = inject_sibling_learnings(
            task_id=task_c_id,
            epic_name="test-mixed-epic",
            db_path=db_path,
        )
        assert result_c is None, "Task C should not receive any learning"

    def test_multiple_targets_single_learning(self, db_path, repo, monkeypatch):
        """Learning targeting multiple tasks (--for B,C) is visible to both."""
        from formaltask.cli.commands import learning as learning_cmd
        from formaltask.cli.exit_codes import ExitCode
        from hooks.session_start.task_context_loader import inject_sibling_learnings

        # Setup
        repo.create_epic("test-multi-target-epic", "Multi-target test")
        task_a_id = repo.create_task("test-multi-target-epic", "Task A", "Source", ["criterion"])
        task_b_id = repo.create_task("test-multi-target-epic", "Task B", "Target 1", ["criterion"])
        task_c_id = repo.create_task("test-multi-target-epic", "Task C", "Target 2", ["criterion"])
        task_d_id = repo.create_task(
            "test-multi-target-epic", "Task D", "Non-target", ["criterion"]
        )

        monkeypatch.setenv("TASK_ID", str(task_a_id))

        # Store learning targeting both B and C
        args = Namespace(
            learning="Shared insight for B and C",
            targets=f"{task_b_id},{task_c_id}",
            db_path=db_path,
        )
        result = learning_cmd.execute(args)
        assert result == ExitCode.SUCCESS

        transition_task_status(db_path, task_a_id, "in_progress")
        transition_task_status(db_path, task_a_id, "completed")

        # Assert: Both B and C receive the learning
        result_b = inject_sibling_learnings(
            task_id=task_b_id,
            epic_name="test-multi-target-epic",
            db_path=db_path,
        )
        assert result_b is not None, "Task B should receive learning"
        assert "Shared insight for B and C" in result_b

        result_c = inject_sibling_learnings(
            task_id=task_c_id,
            epic_name="test-multi-target-epic",
            db_path=db_path,
        )
        assert result_c is not None, "Task C should receive learning"
        assert "Shared insight for B and C" in result_c

        # Assert: D does not receive the learning
        result_d = inject_sibling_learnings(
            task_id=task_d_id,
            epic_name="test-multi-target-epic",
            db_path=db_path,
        )
        assert result_d is None, "Task D should NOT receive learning"
