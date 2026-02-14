"""Tests for task_lifecycle module - transition_task_status() function.

This test suite follows TDD workflow (Red-Green-Refactor):
1. Tests are written first and expected to fail (RED)
2. Implementation is then written to pass them (GREEN)
3. Code is refactored for clarity (REFACTOR)

Tests verify:
- Status transitions with proper timestamp coordination
- Idempotent mode for atomic race condition prevention
- Error handling (invalid status, missing task)
- Edge cases (transition to same status, NULL timestamp handling)
- Database-level defense (trigger independence)
"""

import sqlite3

import pytest

from formaltask.exceptions import TaskNotFoundError
from formaltask.tasks.lifecycle import (
    InvalidTransitionError,
    transition_task_status,
)


class TestTransitionTaskStatus:
    """Tests for transition_task_status() function."""

    def test_transition_to_completed_sets_completed_at(self, db_with_epic_and_tasks):
        """Test that transitioning to 'completed' status sets completed_at timestamp.

        This is the PRIMARY requirement - all completed tasks must have
        completed_at set.

        Note: Must transition through 'in_progress' first per VALID_TRANSITIONS.
        """
        with sqlite3.connect(db_with_epic_and_tasks) as conn:
            # Get a task that's currently 'open' (task 1)
            task_id = 1

            # Before transition, completed_at should be NULL
            cursor = conn.execute(
                "SELECT completed_at FROM tasks WHERE id = ? AND status = 'open'",
                (task_id,),
            )
            result = cursor.fetchone()
            assert result is not None, "Test setup failed: task not found"
            assert result[0] is None, "Test setup failed: completed_at should be NULL"

            # Transition to in_progress first (required by state machine)
            success = transition_task_status(db_with_epic_and_tasks, task_id, "in_progress")
            assert success is True, "Transition to in_progress should succeed"

            # Now transition to completed
            success = transition_task_status(db_with_epic_and_tasks, task_id, "completed")
            assert success is True, "Transition to completed should succeed"

            # Verify status and timestamp are both set
            cursor = conn.execute(
                "SELECT status, completed_at FROM tasks WHERE id = ?",
                (task_id,),
            )
            status, completed_at = cursor.fetchone()
            assert status == "completed", f"Status should be 'completed', got {status}"
            assert completed_at is not None, "completed_at should be set"
            # Verify timestamp format is ISO 8601
            assert "T" in completed_at and "Z" in completed_at, (
                f"Invalid timestamp format: {completed_at}"
            )

    def test_transition_to_completed_records_head_commit_sha(self, db_with_epic_and_tasks):
        """Test that transitioning to 'completed' stores head_commit_sha.

        The head_commit_sha parameter captures the git HEAD at completion time,
        enabling future checks to verify dependency code presence.
        """
        with sqlite3.connect(db_with_epic_and_tasks) as conn:
            task_id = 2  # Another open task

            # Transition to in_progress first (required by state machine)
            transition_task_status(db_with_epic_and_tasks, task_id, "in_progress")

            # Transition to completed WITH head_commit_sha (40 hex chars)
            expected_sha = "abc123def456789012345678901234567890abcd"  # pragma: allowlist secret
            transition_task_status(
                db_with_epic_and_tasks, task_id, "completed", head_commit_sha=expected_sha
            )

            # Verify head_commit_sha is stored
            cursor = conn.execute(
                "SELECT head_commit_sha FROM tasks WHERE id = ?",
                (task_id,),
            )
            actual_sha = cursor.fetchone()[0]
            assert actual_sha == expected_sha, f"Expected SHA '{expected_sha}', got '{actual_sha}'"

    def test_transition_rejects_invalid_sha_format(self, db_with_epic_and_tasks):
        """Test that invalid head_commit_sha format raises ValueError.

        SHA must be exactly 40 hexadecimal characters or None.
        """
        task_id = 2

        # Transition to in_progress first
        transition_task_status(db_with_epic_and_tasks, task_id, "in_progress")

        # Invalid: too short
        with pytest.raises(ValueError, match="Invalid head_commit_sha format"):
            transition_task_status(
                db_with_epic_and_tasks, task_id, "completed", head_commit_sha="abc123"
            )

    def test_transition_to_in_progress_sets_started_at(self, db_with_epic_and_tasks):
        """Test that transitioning to 'in_progress' sets started_at timestamp (if NULL).

        This ensures the atomic protection in task_start.py works correctly:
        if a task is already started, started_at should not be updated again.
        """
        with sqlite3.connect(db_with_epic_and_tasks) as conn:
            task_id = 2  # Another open task

            # Before transition, started_at should be NULL
            cursor = conn.execute(
                "SELECT started_at FROM tasks WHERE id = ? AND status = 'open'",
                (task_id,),
            )
            result = cursor.fetchone()
            assert result is not None, "Test setup failed: task not found"
            assert result[0] is None, "Test setup failed: started_at should be NULL"

            # Transition to in_progress
            success = transition_task_status(db_with_epic_and_tasks, task_id, "in_progress")
            assert success is True, "Transition should succeed"

            # Verify status and started_at are both set
            cursor = conn.execute(
                "SELECT status, started_at FROM tasks WHERE id = ?",
                (task_id,),
            )
            status, started_at = cursor.fetchone()
            assert status == "in_progress", f"Status should be 'in_progress', got {status}"
            assert started_at is not None, "started_at should be set"
            assert "T" in started_at and "Z" in started_at, (
                f"Invalid timestamp format: {started_at}"
            )

    def test_transition_to_in_progress_idempotent_mode(self, db_with_epic_and_tasks):
        """Test idempotent mode for in_progress status.

        When idempotent=True:
        - If task already in state, return False (don't update)
        - If task not in state, update and return True

        This preserves the atomic check-and-update pattern in task_start.py.
        """
        with sqlite3.connect(db_with_epic_and_tasks) as conn:
            task_id = 3  # Task 3 is in_progress

            # First call with idempotent=True on task already in_progress
            # should return False
            success = transition_task_status(
                db_with_epic_and_tasks, task_id, "in_progress", idempotent=True
            )
            assert success is False, "Should return False when already in state (idempotent mode)"

            # Verify status didn't change
            cursor = conn.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
            status = cursor.fetchone()[0]
            assert status == "in_progress", "Status should still be in_progress"

    def test_transition_deferred_no_timestamp(self, db_with_epic_and_tasks):
        """Test that deferring a task doesn't set any timestamp.

        Deferred, pending_merge, blocked, cancelled status don't require
        timestamp coordination - they're not part of the main workflow.
        """
        with sqlite3.connect(db_with_epic_and_tasks) as conn:
            task_id = 2  # An open task

            # Get original timestamps (should be None)
            cursor = conn.execute(
                "SELECT started_at, completed_at FROM tasks WHERE id = ?",
                (task_id,),
            )
            orig_started_at, orig_completed_at = cursor.fetchone()

            # Transition to deferred
            transition_task_status(db_with_epic_and_tasks, task_id, "deferred")

            # Verify timestamps weren't changed
            cursor = conn.execute(
                "SELECT started_at, completed_at FROM tasks WHERE id = ?",
                (task_id,),
            )
            new_started_at, new_completed_at = cursor.fetchone()
            assert new_started_at == orig_started_at, "started_at should not change"
            assert new_completed_at == orig_completed_at, "completed_at should not change"

    def test_transition_pending_merge_no_timestamp(self, db_with_epic_and_tasks):
        """Test that pending_merge status doesn't set completed_at timestamp.

        pending_merge is set by worker_complete.py after PR submission.
        No completed_at timestamp needed for this status.
        Note: Must transition through in_progress first per VALID_TRANSITIONS.
        """
        with sqlite3.connect(db_with_epic_and_tasks) as conn:
            task_id = 2  # An open task

            # Must transition through in_progress first (sets started_at)
            transition_task_status(db_with_epic_and_tasks, task_id, "in_progress")

            # Transition to pending_merge
            transition_task_status(db_with_epic_and_tasks, task_id, "pending_merge")

            # Verify status changed but completed_at not set
            cursor = conn.execute(
                "SELECT status, started_at, completed_at FROM tasks WHERE id = ?",
                (task_id,),
            )
            status, started_at, completed_at = cursor.fetchone()
            assert status == "pending_merge", "Status should be pending_merge"
            assert started_at is not None, "started_at should be set from in_progress transition"
            assert completed_at is None, "completed_at should not be set"

    def test_transition_blocked_no_timestamp(self, db_with_epic_and_tasks):
        """Test that blocked status doesn't set completed_at timestamp.

        blocked is used for tasks waiting on external dependencies.
        No completed_at timestamp coordination needed.
        Note: Must transition through in_progress first per VALID_TRANSITIONS.
        """
        with sqlite3.connect(db_with_epic_and_tasks) as conn:
            task_id = 2  # An open task

            # Must transition through in_progress first (sets started_at)
            transition_task_status(db_with_epic_and_tasks, task_id, "in_progress")

            # Transition to blocked
            transition_task_status(db_with_epic_and_tasks, task_id, "blocked")

            # Verify status changed but completed_at not set
            cursor = conn.execute(
                "SELECT status, started_at, completed_at FROM tasks WHERE id = ?",
                (task_id,),
            )
            status, started_at, completed_at = cursor.fetchone()
            assert status == "blocked", "Status should be blocked"
            assert started_at is not None, "started_at should be set from in_progress transition"
            assert completed_at is None, "completed_at should not be set"

    def test_transition_same_status_raises_error(self, db_with_epic_and_tasks):
        """Test that transitioning to same status raises ValueError.

        In non-idempotent mode (default), attempting to transition to the
        same status is an error condition that should be caught.
        """
        with pytest.raises(ValueError, match="already in status"):
            transition_task_status(db_with_epic_and_tasks, 1, "open")

    def test_transition_same_status_idempotent_returns_false(self, db_with_epic_and_tasks):
        """Test that idempotent mode allows same-status transitions.

        In idempotent mode, it's OK if task is already in the desired state.
        Returns False to indicate no update occurred, but that's expected.
        """
        with sqlite3.connect(db_with_epic_and_tasks):
            task_id = 1  # Task 1 is open

            # Try to transition to 'open' again in idempotent mode
            success = transition_task_status(
                db_with_epic_and_tasks, task_id, "open", idempotent=True
            )
            assert success is False, "Should return False (no update) in idempotent mode"

    def test_transition_invalid_status_raises_value_error(self, db_with_epic_and_tasks):
        """Test that invalid status value raises ValueError.

        Status must be one of: open, in_progress, completed, deferred,
        cancelled, pending_merge, blocked.
        """
        with pytest.raises(ValueError, match="Invalid status"):
            transition_task_status(db_with_epic_and_tasks, 1, "invalid_status")

    def test_transition_missing_task_raises_task_not_found_error(self, db_with_epic_and_tasks):
        """Test that transitioning missing task raises TaskNotFoundError.

        If task_id doesn't exist, function should raise TaskNotFoundError
        (standardized exception from db_helpers.ensure_task_exists).
        """
        with pytest.raises(TaskNotFoundError, match="not found"):
            transition_task_status(db_with_epic_and_tasks, 9999, "open")

    def test_invalid_state_transition_raises_error(self, db_path):
        """Test that invalid state transitions raise InvalidTransitionError with valid targets.

        Verifies:
        1. Transition from terminal state (completed) raises InvalidTransitionError
        2. Error message includes valid transitions list
        3. Error attributes (current_status, new_status, valid_targets) are set correctly

        Per VALID_TRANSITIONS, 'completed' is a terminal state with no valid exits.
        """
        # Create a completed task
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
            )
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at, started_at, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    1,
                    "test-epic",
                    "Completed Task",
                    "Already done",
                    "completed",
                    "2025-01-01T00:00:00Z",
                    "2025-01-01T01:00:00Z",
                    "2025-01-01T02:00:00Z",
                ),
            )
            conn.commit()

        # Attempt invalid transition: completed -> in_progress
        with pytest.raises(InvalidTransitionError) as exc_info:
            transition_task_status(db_path, 1, "in_progress")

        # Verify error attributes
        err = exc_info.value
        assert err.current_status == "completed", (
            f"Expected current='completed', got {err.current_status}"
        )
        assert err.new_status == "in_progress", f"Expected new='in_progress', got {err.new_status}"
        assert err.valid_targets == [], "Terminal state should have no valid targets"

        # Verify error message includes transition info
        error_msg = str(err)
        assert "completed" in error_msg, "Error should mention current status"
        assert "in_progress" in error_msg, "Error should mention attempted status"
        assert "Valid targets" in error_msg or "VALID_TRANSITIONS" in error_msg, (
            f"Error should mention valid transitions, got: {error_msg}"
        )

    def test_exclusive_locking_prevents_race_conditions(self, db_path):
        """Test that exclusive lock is used for atomicity.

        Function should use DatabaseConnection(db_path, exclusive=True)
        to ensure atomic read-check-update sequence.

        This test verifies the pattern by checking that concurrent
        attempts to update the same task don't result in data corruption.
        """
        # Create initial database with a task
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """INSERT INTO epics (name, description, created_at)
                   VALUES (?, ?, ?)""",
                ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
            )
            conn.execute(
                """INSERT INTO tasks
                   (epic_name, title, description, status, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    "test-epic",
                    "Test Task",
                    "Test",
                    "open",
                    "2025-01-01T00:00:00Z",
                ),
            )
            conn.commit()

        # Perform transitions with exclusive locking (must go through in_progress first)
        success = transition_task_status(db_path, 1, "in_progress")
        assert success is True, "Transition to in_progress should succeed"
        success = transition_task_status(db_path, 1, "completed")
        assert success is True, "Transition to completed should succeed"

        # Verify the update was atomic
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT status, completed_at FROM tasks WHERE id = ?",
                (1,),
            )
            result = cursor.fetchone()
            assert result is not None
            status, completed_at = result
            assert status == "completed" and completed_at is not None, (
                "Both status and timestamp must be set atomically"
            )

    def test_force_parameter_bypasses_validation(self, db_with_epic_and_tasks):
        """Test that force=True bypasses Python validation.

        This is used for data repair operations only.
        Force bypasses Python-level validation (ValueError), but database
        CHECK constraints still enforce valid statuses (IntegrityError).
        """
        import sqlite3

        # With force=True, Python validation is skipped (no ValueError)
        # But database CHECK constraint still rejects invalid status
        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            transition_task_status(db_with_epic_and_tasks, 1, "invalid_status", force=True)

        # Verify it's the database constraint, not Python validation
        assert "CHECK constraint" in str(exc_info.value)

    def test_all_seven_status_values_supported(self, db_path):
        """Test that all 7 status values from TaskStatus enum are supported.

        StatusValues:
        - open (initial state)
        - in_progress (sets started_at)
        - completed (sets completed_at)
        - deferred (no timestamp)
        - cancelled (no timestamp)
        - pending_merge (no timestamp)
        - blocked (no timestamp)

        Tests each status via valid transition paths from 'open'.
        Uses db_path (fresh database) instead of db_with_epic_and_tasks
        since we need all tasks to start in 'open' status.
        """
        # Create fresh epic and tasks all in 'open' state
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
                ("test-epic", "Test epic", "2025-01-01T00:00:00Z"),
            )
            for i in range(1, 6):
                conn.execute(
                    """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (i, "test-epic", f"Task {i}", "Description", "open", "2025-01-01T00:00:00Z"),
                )
            conn.commit()

        # Test transitions reachable from open state (uses different tasks to avoid conflicts)
        # Task 1: open -> in_progress -> completed
        transition_task_status(db_path, 1, "in_progress")
        transition_task_status(db_path, 1, "completed")

        # Task 2: open -> in_progress -> deferred
        transition_task_status(db_path, 2, "in_progress")
        transition_task_status(db_path, 2, "deferred")

        # Task 3: open -> cancelled
        transition_task_status(db_path, 3, "cancelled")

        # Task 4: open -> in_progress -> blocked (blocked only reachable from in_progress)
        transition_task_status(db_path, 4, "in_progress")
        transition_task_status(db_path, 4, "blocked")

        # Task 5: open -> in_progress -> pending_merge
        transition_task_status(db_path, 5, "in_progress")
        transition_task_status(db_path, 5, "pending_merge")

        # Verify all transitions succeeded by checking final states
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT id, status FROM tasks ORDER BY id")
            results = {row[0]: row[1] for row in cursor.fetchall()}
            assert results[1] == "completed"
            assert results[2] == "deferred"
            assert results[3] == "cancelled"
            assert results[4] == "blocked"
            assert results[5] == "pending_merge"


class TestTransitionTaskStatusTriggerIndependence:
    """Tests verifying trigger works as defense-in-depth for bypassed code.

    These tests verify that if a code path bypasses transition_task_status()
    and does direct SQL, the database trigger will still set timestamps.

    Triggers defined in schema-v5.sql (added from migration 017):
    - set_completed_at_on_completion: Auto-sets completed_at when status='completed'
    - set_started_at_on_start: Auto-sets started_at when status='in_progress'
    """

    def test_direct_sql_completed_update_fires_trigger(self, db_with_epic_and_tasks):
        """Test that direct SQL UPDATE status='completed' triggers timestamp.

        Simulates a bug where code does:
            UPDATE tasks SET status = 'completed' WHERE id = ?

        The trigger should:
            WHEN NEW.status = 'completed' AND NEW.completed_at IS NULL
            BEGIN UPDATE tasks SET completed_at = ... END
        """
        with sqlite3.connect(db_with_epic_and_tasks) as conn:
            task_id = 1  # An open task

            # Verify completed_at is NULL before update
            cursor = conn.execute("SELECT completed_at FROM tasks WHERE id = ?", (task_id,))
            assert cursor.fetchone()[0] is None, "Test setup: completed_at should be NULL"

            # Direct SQL update WITHOUT setting completed_at (simulates buggy code)
            conn.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))
            conn.commit()

            # Trigger should have auto-populated completed_at
            cursor = conn.execute("SELECT status, completed_at FROM tasks WHERE id = ?", (task_id,))
            status, completed_at = cursor.fetchone()
            assert status == "completed", f"Status should be 'completed', got {status}"
            assert completed_at is not None, "Trigger should have set completed_at"
            # Verify ISO 8601 format
            assert "T" in completed_at and completed_at.endswith("Z"), (
                f"Timestamp should be ISO 8601 with Z suffix, got {completed_at}"
            )

    def test_direct_sql_with_explicit_timestamp_trigger_does_not_fire(self, db_with_epic_and_tasks):
        """Test that trigger doesn't double-update when timestamp already set.

        If code does:
            UPDATE tasks SET status = 'completed', completed_at = '...' WHERE id = ?

        The trigger should NOT fire because NEW.completed_at IS NOT NULL.
        """
        with sqlite3.connect(db_with_epic_and_tasks) as conn:
            task_id = 2  # Another open task

            # Set a specific timestamp that we can verify is preserved
            explicit_timestamp = "2025-01-15T12:00:00Z"

            # Update with EXPLICIT completed_at (correct code pattern)
            conn.execute(
                "UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ?",
                (explicit_timestamp, task_id),
            )
            conn.commit()

            # Trigger should NOT have overwritten our explicit timestamp
            cursor = conn.execute("SELECT completed_at FROM tasks WHERE id = ?", (task_id,))
            actual_timestamp = cursor.fetchone()[0]
            assert actual_timestamp == explicit_timestamp, (
                f"Trigger should NOT overwrite explicit timestamp. "
                f"Expected {explicit_timestamp}, got {actual_timestamp}"
            )

    def test_direct_sql_with_explicit_started_at_trigger_does_not_fire(
        self, db_with_epic_and_tasks
    ):
        """Test that trigger doesn't double-update when started_at already set.

        If code does:
            UPDATE tasks SET status = 'in_progress', started_at = '...' WHERE id = ?

        The trigger should NOT fire because NEW.started_at IS NOT NULL.
        """
        with sqlite3.connect(db_with_epic_and_tasks) as conn:
            task_id = 1  # An open task (different from other tests)

            # Set a specific timestamp that we can verify is preserved
            explicit_timestamp = "2025-01-15T08:30:00Z"

            # Update with EXPLICIT started_at (correct code pattern)
            conn.execute(
                "UPDATE tasks SET status = 'in_progress', started_at = ? WHERE id = ?",
                (explicit_timestamp, task_id),
            )
            conn.commit()

            # Trigger should NOT have overwritten our explicit timestamp
            cursor = conn.execute("SELECT started_at FROM tasks WHERE id = ?", (task_id,))
            actual_timestamp = cursor.fetchone()[0]
            assert actual_timestamp == explicit_timestamp, (
                f"Trigger should NOT overwrite explicit timestamp. "
                f"Expected {explicit_timestamp}, got {actual_timestamp}"
            )

    def test_direct_sql_in_progress_update_fires_trigger(self, db_with_epic_and_tasks):
        """Test that direct SQL UPDATE status='in_progress' triggers timestamp.

        Similar to completed_at test but for started_at.
        """
        with sqlite3.connect(db_with_epic_and_tasks) as conn:
            task_id = 2  # An open task (use different from completed test)

            # Verify started_at is NULL before update
            cursor = conn.execute("SELECT started_at FROM tasks WHERE id = ?", (task_id,))
            assert cursor.fetchone()[0] is None, "Test setup: started_at should be NULL"

            # Direct SQL update WITHOUT setting started_at (simulates buggy code)
            conn.execute("UPDATE tasks SET status = 'in_progress' WHERE id = ?", (task_id,))
            conn.commit()

            # Trigger should have auto-populated started_at
            cursor = conn.execute("SELECT status, started_at FROM tasks WHERE id = ?", (task_id,))
            status, started_at = cursor.fetchone()
            assert status == "in_progress", f"Status should be 'in_progress', got {status}"
            assert started_at is not None, "Trigger should have set started_at"
            # Verify ISO 8601 format
            assert "T" in started_at and started_at.endswith("Z"), (
                f"Timestamp should be ISO 8601 with Z suffix, got {started_at}"
            )
