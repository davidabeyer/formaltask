#!/usr/bin/env python3
"""Unit tests for worker health analyzer module.

Phase 2: Enhanced Status Command - Unit Tests
Tests worker_health_analyzer functions for state detection and extraction.

Task #2666: TestGetNudgeCount, TestIsRecovering, TestTruncateTitle removed.
- get_nudge_count() deleted (dead code - nothing creates nudge files)
- is_recovering() deleted (dead code - nothing creates recovery logs)
- truncate_title() inlined into get_worker_state_dict()
Task #2691: STALENESS_THRESHOLD moved from manager.py to health.py.
"""

import pytest

from formaltask.workers.health import is_task_session


class TestIsTaskSession:
    """Test session name validation."""

    def test_validate_valid_session_name(self):
        """Should accept task-{digits} format."""
        assert is_task_session("task-42") is True
        assert is_task_session("task-0") is True
        assert is_task_session("task-999999") is True

    def test_validate_invalid_prefix(self):
        """Should reject non-task prefix."""
        assert is_task_session("worker-42") is False
        assert is_task_session("tmux-42") is False

    def test_validate_invalid_suffix(self):
        """Should reject non-numeric suffix."""
        assert is_task_session("task-abc") is False
        assert is_task_session("task-") is False

    def test_validate_empty_string(self):
        """Should reject empty string."""
        assert is_task_session("") is False


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_get_worker_state_dict_detects_crashed_worker(self, tmp_path, monkeypatch):
        """get_worker_state_dict should detect crashed workers (running state + no tmux session).

        Task #1732: When state file shows running state but tmux session is dead,
        should return health_state='exited'.

        Task #1986: Must mock derive_worker_phase() to return a running phase
        (like "implementing") so crash detection logic is triggered.

        Task #2653: read_state removed (workers table deleted) - staleness now from transcript mtime.
        """
        from unittest.mock import patch

        # Mock tmux session check to return False (session doesn't exist)
        # Mock derive_worker_phase_with_pr to return a running phase so crash detection triggers
        from formaltask.core.completion_check import CompletionCheck
        from formaltask.workers.health import get_worker_state_dict

        with (
            patch("formaltask.workers.health.is_task_session", return_value=True),
            patch("formaltask.workers.health.tmux_session_exists", return_value=False),
            patch(
                "formaltask.workers.health.check_completion",
                return_value=CompletionCheck(
                    allowed=True, phase="implementing", reason=None, pr_info=None
                ),
            ),
        ):
            # db_path required for check_completion to be called
            result = get_worker_state_dict(task_id=50, session_name="task-50", db_path="/fake/db")

            # Should detect crashed state (implementing + no tmux = exited)
            assert result["health_state"] == "exited"


class TestGetWorkerStateDictGitFields:
    """Test git status fields in get_worker_state_dict.

    Task #1872: Extend get_worker_state_dict with git status fields.
    Tests has_commits, pr_number, pr_status fields.
    Note: finding_counts was removed as dead code in Task #2274.
    """

    def test_worker_state_dict_includes_pr_number(self):
        """pr_number key should be present and be int or None."""
        from formaltask.workers.health import get_worker_state_dict

        state = get_worker_state_dict(task_id=999999, session_name="task-999999")

        assert "pr_number" in state, "pr_number key must be present"
        assert state["pr_number"] is None or isinstance(state["pr_number"], int), (
            f"pr_number should be int or None, got {type(state['pr_number']).__name__}"
        )

    def test_worker_state_dict_includes_pr_status(self):
        """pr_status key should be present and be valid PRStatus value."""
        from formaltask.workers.health import get_worker_state_dict

        state = get_worker_state_dict(task_id=999999, session_name="task-999999")

        assert "pr_status" in state, "pr_status key must be present"
        valid_statuses = {"none", "open", "merged", "closed", "error"}
        assert state["pr_status"] in valid_statuses, (
            f"pr_status should be one of {valid_statuses}, got {state['pr_status']}"
        )

    def test_worker_state_dict_pr_status_merged(self, tmp_path):
        """pr_status should return 'merged' for merged PR via get_pr_for_task."""
        import sqlite3
        from unittest.mock import patch

        from formaltask.git.github import PRInfo
        from formaltask.workers.health import get_worker_state_dict

        # Create temp database (github_pr_number not used anymore)
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    title TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commits (
                    id INTEGER PRIMARY KEY,
                    task_id INTEGER
                )
            """)
            cursor.execute("INSERT INTO tasks (id, title) VALUES (42, 'Test task')")
            conn.commit()

        # Task #2251: PR info now comes from derive_worker_phase_with_pr
        from formaltask.core.completion_check import CompletionCheck

        mock_pr_info = PRInfo(number=1725, state="MERGED", merged=True)
        with (
            patch("formaltask.workers.health.tmux_session_exists", return_value=True),
            patch(
                "formaltask.workers.health.check_completion",
                return_value=CompletionCheck(
                    allowed=True, phase="done", reason=None, pr_info=mock_pr_info
                ),
            ),
        ):
            state = get_worker_state_dict(task_id=42, session_name="task-42", db_path=str(db_path))

        assert state["pr_number"] == 1725
        assert state["pr_status"] == "merged"

    def test_worker_state_dict_pr_status_open(self, tmp_path):
        """pr_status should return 'open' for open PR via derive_worker_phase_with_pr."""
        import sqlite3
        from unittest.mock import patch

        from formaltask.core.completion_check import CompletionCheck
        from formaltask.git.github import PRInfo
        from formaltask.workers.health import get_worker_state_dict

        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    title TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commits (
                    id INTEGER PRIMARY KEY,
                    task_id INTEGER
                )
            """)
            cursor.execute("INSERT INTO tasks (id, title) VALUES (42, 'Test task')")
            conn.commit()

        # Task #2251: PR info now comes from derive_worker_phase_with_pr
        mock_pr_info = PRInfo(number=1800, state="OPEN", merged=False)
        with (
            patch("formaltask.workers.health.tmux_session_exists", return_value=True),
            patch(
                "formaltask.workers.health.check_completion",
                return_value=CompletionCheck(
                    allowed=True, phase="awaiting_merge", reason=None, pr_info=mock_pr_info
                ),
            ),
        ):
            state = get_worker_state_dict(task_id=42, session_name="task-42", db_path=str(db_path))

        assert state["pr_number"] == 1800
        assert state["pr_status"] == "open"

    def test_worker_state_dict_pr_status_closed(self, tmp_path):
        """pr_status should return 'closed' for closed PR via derive_worker_phase_with_pr."""
        import sqlite3
        from unittest.mock import patch

        from formaltask.core.completion_check import CompletionCheck
        from formaltask.git.github import PRInfo
        from formaltask.workers.health import get_worker_state_dict

        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    title TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commits (
                    id INTEGER PRIMARY KEY,
                    task_id INTEGER
                )
            """)
            cursor.execute("INSERT INTO tasks (id, title) VALUES (42, 'Test task')")
            conn.commit()

        # Task #2251: PR info now comes from derive_worker_phase_with_pr
        mock_pr_info = PRInfo(number=1801, state="CLOSED", merged=False)
        with (
            patch("formaltask.workers.health.tmux_session_exists", return_value=True),
            patch(
                "formaltask.workers.health.check_completion",
                return_value=CompletionCheck(
                    allowed=True, phase="needs_pr", reason=None, pr_info=mock_pr_info
                ),
            ),
        ):
            state = get_worker_state_dict(task_id=42, session_name="task-42", db_path=str(db_path))

        assert state["pr_number"] == 1801
        assert state["pr_status"] == "closed"

    def test_worker_state_dict_pr_status_handles_no_phase_result(self, tmp_path):
        """pr_status should return 'none' when derive_worker_phase_with_pr returns None."""
        import sqlite3
        from unittest.mock import patch

        from formaltask.workers.health import get_worker_state_dict

        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    title TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commits (
                    id INTEGER PRIMARY KEY,
                    task_id INTEGER
                )
            """)
            cursor.execute("INSERT INTO tasks (id, title) VALUES (42, 'Test task')")
            conn.commit()

        # Task #2251: When derive_worker_phase_with_pr returns None, PR fields should be defaults
        with (
            patch("formaltask.workers.health.tmux_session_exists", return_value=True),
            patch(
                "formaltask.workers.health.check_completion",
                return_value=None,
            ),
        ):
            state = get_worker_state_dict(task_id=42, session_name="task-42", db_path=str(db_path))

        # Should gracefully return defaults when no phase result
        assert state["pr_number"] is None
        assert state["pr_status"] == "none"


class TestGetWorkerStateDictDerivedPhase:
    """Test get_worker_state_dict() uses check_completion() for health_state.

    Task #1986: Dashboard should show gate-verified phase derived from task state,
    reviews, and PR status - not self-reported @@@HANDOFF fsm_state.

    Acceptance criteria:
    1. Dashboard shows 'implementing' when no reviews exist
    2. Dashboard shows 'needs_fix' when P2/P3 findings present
    3. Dashboard shows 'needs_pr' when reviews clean but no PR
    4. Dashboard shows 'awaiting_merge' when PR exists but not merged
    5. No dependency on @@@HANDOFF phase field for display
    """

    @pytest.fixture(autouse=True)
    def disable_freshness_check(self, monkeypatch):
        """Disable stale review check for phase derivation tests.

        These tests verify phase derivation logic, not review freshness.
        Mocking git operations would add complexity without testing value.
        """
        from formaltask.core import rules_config as rules

        monkeypatch.setattr(rules, "CHECK_FRESHNESS", False)

    def test_implementing_when_no_reviews(self, db_path):
        """Dashboard shows 'implementing' when no reviews exist for task.

        Acceptance criterion #1: A task with no reviews in task_reviews
        should show health_state='implementing'.
        """
        from unittest.mock import patch

        from formaltask.db.connection import DatabaseConnection
        from formaltask.workers.health import get_worker_state_dict

        # Create epic and task with no reviews
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                """INSERT INTO epics (name, description, created_at)
                   VALUES ('test-epic', 'Test epic', datetime('now'))"""
            )
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (42, 'test-epic', 'Test task', 'Description', 'in_progress', datetime('now'))"""
            )

        with patch("formaltask.workers.health.tmux_session_exists", return_value=True):
            state = get_worker_state_dict(task_id=42, session_name="task-42", db_path=str(db_path))

        # No reviews = implementing phase
        assert state["health_state"] == "implementing"

    def test_needs_fix_when_blocking_findings(self, db_path):
        """Dashboard shows 'needs_fix' when blocking priority findings present.

        Acceptance criterion #2: A task with P0 or P1 findings in reviews
        should show health_state='needs_fix'. P2/P3 are non-blocking.
        """
        import json
        from unittest.mock import patch

        from formaltask.db.connection import DatabaseConnection
        from formaltask.workers.health import get_worker_state_dict

        # Create epic, task, and review with P1 finding (blocking priority)
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                """INSERT INTO epics (name, description, created_at)
                   VALUES ('test-epic', 'Test epic', datetime('now'))"""
            )
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (42, 'test-epic', 'Test task', 'Description', 'in_progress', datetime('now'))"""
            )
            findings = json.dumps([{"priority": "P1", "message": "Critical issue"}])
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at)
                   VALUES (42, 'code-quality', 'critical', ?, datetime('now'))""",
                (findings,),
            )

        with patch("formaltask.workers.health.tmux_session_exists", return_value=True):
            state = get_worker_state_dict(task_id=42, session_name="task-42", db_path=str(db_path))

        # P1 finding (blocking) = needs_fix phase
        assert state["health_state"] == "needs_fix"

    def test_needs_pr_when_reviews_clean_no_pr(self, db_path):
        """Dashboard shows 'needs_pr' when reviews clean but no PR.

        Acceptance criterion #3: A task with clean reviews but no PR
        should show health_state='needs_pr'.
        """
        import json
        from unittest.mock import patch

        from formaltask.db.connection import DatabaseConnection
        from formaltask.workers.health import get_worker_state_dict

        # Create epic, task, and clean review (no PR)
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                """INSERT INTO epics (name, description, created_at)
                   VALUES ('test-epic', 'Test epic', datetime('now'))"""
            )
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (42, 'test-epic', 'Test task', 'Description', 'in_progress', datetime('now'))"""
            )
            # Clean review (empty findings)
            findings = json.dumps([])
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at)
                   VALUES (42, 'code-quality', 'clean', ?, datetime('now'))""",
                (findings,),
            )

        with patch("formaltask.workers.health.tmux_session_exists", return_value=True):
            state = get_worker_state_dict(task_id=42, session_name="task-42", db_path=str(db_path))

        # Clean reviews + no PR = needs_pr phase
        assert state["health_state"] == "needs_pr"

    def test_awaiting_merge_when_pr_exists_not_merged(self, db_path):
        """Dashboard shows 'awaiting_merge' when PR exists but not merged.

        Acceptance criterion #4: A task with clean reviews and open PR
        should show health_state='awaiting_merge'.
        Task #2182: Updated to mock get_pr_for_task for GitHub API queries.
        """
        import json
        from unittest.mock import patch

        from formaltask.db.connection import DatabaseConnection
        from formaltask.git.github import PRInfo
        from formaltask.workers.health import get_worker_state_dict

        # Create epic, task, and clean review
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                """INSERT INTO epics (name, description, created_at)
                   VALUES ('test-epic', 'Test epic', datetime('now'))"""
            )
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (42, 'test-epic', 'Test task', 'Description', 'in_progress', datetime('now'))"""
            )
            # Clean review
            findings = json.dumps([])
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at)
                   VALUES (42, 'code-quality', 'clean', ?, datetime('now'))""",
                (findings,),
            )

        with (
            patch("formaltask.workers.health.tmux_session_exists", return_value=True),
            patch(
                "formaltask.git.github.get_pr_for_task",
                return_value=PRInfo(number=123, state="OPEN", merged=False),
            ),
        ):
            state = get_worker_state_dict(task_id=42, session_name="task-42", db_path=str(db_path))

        # PR exists, not merged = awaiting_merge phase
        assert state["health_state"] == "awaiting_merge"

    def test_needs_fix_when_unresolved_findings(self, db_path):
        """Dashboard shows 'needs_fix' when unresolved findings present.

        Task #1986: Unresolved P0-P3 findings get needs_fix phase.
        Worker must address or escalate (set needshuman disposition) for needs_human.
        """
        import json
        from unittest.mock import patch

        from formaltask.db.connection import DatabaseConnection
        from formaltask.workers.health import get_worker_state_dict

        # Create epic, task, and review with P1 finding (no disposition)
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                """INSERT INTO epics (name, description, created_at)
                   VALUES ('test-epic', 'Test epic', datetime('now'))"""
            )
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (42, 'test-epic', 'Test task', 'Description', 'in_progress', datetime('now'))"""
            )
            findings = json.dumps([{"priority": "P1", "message": "Critical security issue"}])
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at)
                   VALUES (42, 'code-quality', 'critical', ?, datetime('now'))""",
                (findings,),
            )

        with patch("formaltask.workers.health.tmux_session_exists", return_value=True):
            state = get_worker_state_dict(task_id=42, session_name="task-42", db_path=str(db_path))

        # Unresolved finding (no disposition) = needs_fix phase
        assert state["health_state"] == "needs_fix"

    def test_done_when_task_completed(self, db_path):
        """Dashboard shows 'done' when task status is 'completed'.

        Task #1986: Completed tasks should show done phase.
        Task #2318: Updated to require merged PR for 'done' status.
        """
        from unittest.mock import patch

        from formaltask.db.connection import DatabaseConnection
        from formaltask.git.github import PRInfo
        from formaltask.workers.health import get_worker_state_dict

        # Create epic and completed task
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                """INSERT INTO epics (name, description, created_at)
                   VALUES ('test-epic', 'Test epic', datetime('now'))"""
            )
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (42, 'test-epic', 'Test task', 'Description', 'completed', datetime('now'))"""
            )

        # Task #2318: Completed tasks gate on PR status - mock merged PR
        with (
            patch("formaltask.workers.health.tmux_session_exists", return_value=True),
            patch(
                "formaltask.git.github.get_pr_for_task",
                return_value=PRInfo(number=123, state="MERGED", merged=True),
            ),
        ):
            state = get_worker_state_dict(task_id=42, session_name="task-42", db_path=str(db_path))

        # Completed task with merged PR = done phase
        assert state["health_state"] == "done"

    def test_done_when_pr_merged(self, db_path):
        """Dashboard shows 'done' when PR is merged.

        Task #1986: A merged PR indicates task completion even if
        status hasn't been updated yet.
        Task #2182: Updated to mock get_pr_for_task for GitHub API queries.
        """
        import json
        from unittest.mock import patch

        from formaltask.db.connection import DatabaseConnection
        from formaltask.git.github import PRInfo
        from formaltask.workers.health import get_worker_state_dict

        # Create epic, task, and clean review
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                """INSERT INTO epics (name, description, created_at)
                   VALUES ('test-epic', 'Test epic', datetime('now'))"""
            )
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (42, 'test-epic', 'Test task', 'Description', 'in_progress', datetime('now'))"""
            )
            # Add clean review
            findings = json.dumps([])
            conn.execute(
                """INSERT INTO task_reviews (task_id, review_type, severity, findings, reviewed_at)
                   VALUES (42, 'code-quality', 'clean', ?, datetime('now'))""",
                (findings,),
            )

        with (
            patch("formaltask.workers.health.tmux_session_exists", return_value=True),
            patch(
                "formaltask.git.github.get_pr_for_task",
                return_value=PRInfo(number=123, state="MERGED", merged=True),
            ),
        ):
            state = get_worker_state_dict(task_id=42, session_name="task-42", db_path=str(db_path))

        # PR merged = done phase
        assert state["health_state"] == "done"

    def test_ignores_self_reported_fsm_state(self, db_path):
        """health_state should not depend on self-reported fsm_state.

        Acceptance criterion #5: No dependency on @@@HANDOFF phase field for display.
        The dashboard shows derived phase based on gate states (task status, reviews, PR).

        Task #2653: read_state removed (workers table deleted) - this test now verifies
        derive_worker_phase_with_pr is used instead.
        """
        from unittest.mock import patch

        from formaltask.db.connection import DatabaseConnection
        from formaltask.workers.health import get_worker_state_dict

        # Create task with no reviews
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                """INSERT INTO epics (name, description, created_at)
                   VALUES ('test-epic', 'Test epic', datetime('now'))"""
            )
            conn.execute(
                """INSERT INTO tasks (id, epic_name, title, description, status, created_at)
                   VALUES (42, 'test-epic', 'Test task', 'Description', 'in_progress', datetime('now'))"""
            )

        with patch("formaltask.workers.health.tmux_session_exists", return_value=True):
            state = get_worker_state_dict(task_id=42, session_name="task-42", db_path=str(db_path))

        # Should show 'implementing' (derived from task having no reviews)
        assert state["health_state"] == "implementing"

    def test_derive_worker_phase_failure_falls_back_to_unknown(self, tmp_path):
        """When derive_worker_phase_with_pr returns None, health_state should be 'unknown'.

        Edge case: If task doesn't exist or database error, fallback gracefully.
        Task #2251: Changed from derive_worker_phase to derive_worker_phase_with_pr.
        Task #2653: read_state removed (workers table deleted).
        """
        from unittest.mock import patch

        from formaltask.workers.health import get_worker_state_dict

        with (
            patch("formaltask.workers.health.check_completion", return_value=None),
            patch("formaltask.workers.health.tmux_session_exists", return_value=True),
        ):
            state = get_worker_state_dict(
                task_id=99999,
                session_name="task-99999",
                db_path=str(tmp_path / "nonexistent.db"),
            )

        # Fallback to unknown when derive_worker_phase_with_pr returns None
        assert state["health_state"] == "unknown"


class TestGetWorkerStateDictWorktreePath:
    """Test worktree_path field in get_worker_state_dict.

    Task #2135: Add worktree_path field for git stats support.
    """

    def test_worker_state_dict_includes_worktree_path(self):
        """worktree_path key should be present and be a string."""
        from formaltask.workers.health import get_worker_state_dict

        state = get_worker_state_dict(task_id=999999, session_name="task-999999")

        assert "worktree_path" in state, "worktree_path key must be present"
        assert isinstance(state["worktree_path"], str), (
            f"worktree_path should be str, got {type(state['worktree_path']).__name__}"
        )

    def test_worktree_path_valid_when_exists(self, tmp_path, monkeypatch):
        """worktree_path should contain valid path when worktree exists."""
        from unittest.mock import patch

        from formaltask.workers.health import get_worker_state_dict

        # Create a mock worktree directory
        mock_worktree = tmp_path / ".claude" / "worktrees" / "task-42"
        mock_worktree.mkdir(parents=True)

        # Mock Path.home() to return tmp_path for consistent testing
        with (
            patch("formaltask.paths.Path.home", return_value=tmp_path),
            patch("formaltask.workers.health.tmux_session_exists", return_value=True),
        ):
            state = get_worker_state_dict(task_id=42, session_name="task-42")

        expected_path = str(mock_worktree)
        assert state["worktree_path"] == expected_path

    def test_worktree_path_empty_when_not_exists(self):
        """worktree_path should be empty string when worktree doesn't exist."""
        from formaltask.workers.health import get_worker_state_dict

        # Use non-existent task ID - worktree won't exist
        state = get_worker_state_dict(task_id=888888, session_name="task-888888")

        assert state["worktree_path"] == ""

    def test_worktree_path_computed_for_invalid_session(self, tmp_path):
        """worktree_path should be computed even when session name is invalid."""
        from unittest.mock import patch

        from formaltask.workers.health import get_worker_state_dict

        # Create a worktree directory for task-42
        mock_worktree = tmp_path / ".claude" / "worktrees" / "task-42"
        mock_worktree.mkdir(parents=True)

        # Use invalid session name to trigger early return path
        with patch("formaltask.paths.Path.home", return_value=tmp_path):
            state = get_worker_state_dict(task_id=42, session_name="invalid-session")

        # Even with invalid session, worktree_path should be computed
        expected_path = str(mock_worktree)
        assert state["worktree_path"] == expected_path

    def test_worktree_path_no_exception_on_path_error(self):
        """worktree_path should return empty string on path errors, not raise.

        Task #2653: read_state removed (workers table deleted).
        """
        from pathlib import Path
        from unittest.mock import patch

        from formaltask.workers.health import get_worker_state_dict

        # Mock Path.exists() to raise OSError (simulates filesystem error)
        original_exists = Path.exists

        def mock_exists(self):
            if "worktrees" in str(self):
                raise OSError("Filesystem error")
            return original_exists(self)

        with (
            patch.object(Path, "exists", mock_exists),
            patch("formaltask.workers.health.tmux_session_exists", return_value=True),
            # Mock derive_worker_phase_with_pr to avoid DB path lookup
            patch("formaltask.workers.health.check_completion", return_value=None),
            # Mock get_transcript_mtime to avoid DB path lookup (also uses Path.exists)
            patch("formaltask.workers.health.get_transcript_mtime", return_value=None),
        ):
            # Should not raise, should return empty string
            state = get_worker_state_dict(task_id=42, session_name="task-42")

        assert state["worktree_path"] == ""


class TestCommitsAhead:
    """Test commits_ahead field in worker state dict (Task #2297)."""

    def test_worker_state_dict_includes_commits_ahead(self):
        """commits_ahead key should be present and be an integer."""
        from formaltask.workers.health import get_worker_state_dict

        state = get_worker_state_dict(task_id=999999, session_name="task-999999")

        assert "commits_ahead" in state, "commits_ahead key must be present"
        assert isinstance(state["commits_ahead"], int), (
            f"commits_ahead should be int, got {type(state['commits_ahead']).__name__}"
        )


class TestGetWorkerStateDictGitHubPRUtils:
    """Test get_worker_state_dict uses derive_worker_phase_with_pr for PR lookups.

    Task #2181: Replace database github_pr_number column with github_pr_utils
    batch queries for PR information.
    Task #2251: PR info now comes from derive_worker_phase_with_pr to eliminate
    duplicate GitHub API calls.
    """

    def test_pr_status_merged_from_phase_result(self, tmp_path):
        """pr_status should be 'merged' when PhaseResult contains merged PR."""
        import sqlite3
        from unittest.mock import patch

        from formaltask.core.completion_check import CompletionCheck
        from formaltask.git.github import PRInfo
        from formaltask.workers.health import get_worker_state_dict

        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    title TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commits (
                    id INTEGER PRIMARY KEY,
                    task_id INTEGER
                )
            """)
            cursor.execute("INSERT INTO tasks (id, title) VALUES (42, 'Test task')")
            conn.commit()

        # Task #2251: PR info comes from PhaseResult
        mock_pr_info = PRInfo(number=2000, state="MERGED", merged=True)
        mock_phase_result = CompletionCheck(
            allowed=True, phase="done", reason=None, pr_info=mock_pr_info
        )

        with (
            patch("formaltask.workers.health.tmux_session_exists", return_value=True),
            patch(
                "formaltask.workers.health.check_completion",
                return_value=mock_phase_result,
            ),
        ):
            state = get_worker_state_dict(task_id=42, session_name="task-42", db_path=str(db_path))

        assert state["pr_number"] == 2000
        assert state["pr_status"] == "merged"

    def test_pr_status_closed_from_phase_result(self, tmp_path):
        """pr_status should be 'closed' when PhaseResult contains closed PR."""
        import sqlite3
        from unittest.mock import patch

        from formaltask.core.completion_check import CompletionCheck
        from formaltask.git.github import PRInfo
        from formaltask.workers.health import get_worker_state_dict

        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    title TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commits (
                    id INTEGER PRIMARY KEY,
                    task_id INTEGER
                )
            """)
            cursor.execute("INSERT INTO tasks (id, title) VALUES (42, 'Test task')")
            conn.commit()

        # Task #2251: PR info comes from PhaseResult
        mock_pr_info = PRInfo(number=2001, state="CLOSED", merged=False)
        mock_phase_result = CompletionCheck(
            allowed=True, phase="needs_pr", reason=None, pr_info=mock_pr_info
        )

        with (
            patch("formaltask.workers.health.tmux_session_exists", return_value=True),
            patch(
                "formaltask.workers.health.check_completion",
                return_value=mock_phase_result,
            ),
        ):
            state = get_worker_state_dict(task_id=42, session_name="task-42", db_path=str(db_path))

        assert state["pr_number"] == 2001
        assert state["pr_status"] == "closed"

    def test_pr_status_none_when_no_pr_in_phase_result(self, tmp_path):
        """pr_status should be 'none' when PhaseResult has pr_info=None."""
        import sqlite3
        from unittest.mock import patch

        from formaltask.core.completion_check import CompletionCheck
        from formaltask.workers.health import get_worker_state_dict

        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    title TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commits (
                    id INTEGER PRIMARY KEY,
                    task_id INTEGER
                )
            """)
            cursor.execute("INSERT INTO tasks (id, title) VALUES (42, 'Test task')")
            conn.commit()

        # Task #2251: PhaseResult with pr_info=None means no PR exists
        mock_phase_result = CompletionCheck(
            allowed=True, phase="needs_pr", reason=None, pr_info=None
        )

        with (
            patch("formaltask.workers.health.tmux_session_exists", return_value=True),
            patch(
                "formaltask.workers.health.check_completion",
                return_value=mock_phase_result,
            ),
        ):
            state = get_worker_state_dict(task_id=42, session_name="task-42", db_path=str(db_path))

        assert state["pr_number"] is None
        assert state["pr_status"] == "none"


