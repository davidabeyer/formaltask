"""Integration tests for IPC flow (Task #1292).

End-to-end tests for the worker detection → classification → DB update flow.
Tests actual subprocess execution and database transitions, not dict/enum internals.
"""

import json
import os
import subprocess
import sys

import pytest

# =============================================================================
# Stop Hook Classification Tests
# =============================================================================


class TestStopHookClassification:
    """Tests for Stop hook classification of worker completion status."""

    @pytest.fixture
    def stop_hook_script(self):
        """Path to the stop_worker_detection.py script."""
        from tests.fixtures.paths import HOOKS_DIR

        return HOOKS_DIR / "stop_worker_detection.py"

    @pytest.fixture
    def mock_env(self, tmp_path, monkeypatch):
        """Set up mock environment for hook execution."""
        # Create temporary .task directory with task ID
        task_dir = tmp_path / ".task"
        task_dir.mkdir()
        (task_dir / "id").write_text("42")

        # Create mock database
        db_path = tmp_path / "formaltask.db"
        db_path.write_text("")  # Empty file for mock

        monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
        return tmp_path

    def test_stop_hook_outputs_json(self, stop_hook_script, mock_env):
        """Stop hook outputs valid JSON for Claude Code hook protocol.

        Uses environment control instead of patching - patches don't cross
        subprocess boundaries. By NOT setting TMUX, is_worker_session()
        returns (False, None), ensuring the non-worker code path.
        """
        if not stop_hook_script.exists():
            pytest.skip("stop_worker_detection.py not found")

        # Control behavior via environment, not patching
        # No TMUX → is_worker_session returns (False, None)
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PROJECT_ROOT": str(mock_env),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            # Deliberately omit TMUX to ensure non-worker path
        }

        result = subprocess.run(
            [sys.executable, str(stop_hook_script)],
            capture_output=True,
            text=True,
            cwd=str(mock_env),
            env=env,
        )

        # Hook must output valid JSON with "approve" decision
        output = json.loads(result.stdout)
        assert output["decision"] == "approve"


# =============================================================================
# Database Update Tests
# =============================================================================


class TestDatabaseStatusUpdates:
    """Tests for task status updates from IPC flow."""

    @pytest.fixture
    def db_with_task(self, tmp_path):
        """Create database with a task for testing.

        Schema must include started_at and completed_at for task_lifecycle.py.
        """
        import sqlite3

        db_path = tmp_path / "formaltask.db"
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Create schema with all required columns for task_lifecycle
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    epic_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    metadata TEXT
                )
                """
            )

            # Insert test task in in_progress state (with started_at set)
            cursor.execute(
                """
                INSERT INTO tasks (id, epic_name, title, description, status, created_at, started_at)
                VALUES (42, 'test-epic', 'Test Task', 'Description', 'in_progress', '2025-01-01T00:00:00Z', '2025-01-01T00:01:00Z')
                """
            )
            conn.commit()

        return db_path

    def test_transition_to_pending_review(self, db_with_task):
        """Task can transition from in_progress to pending_review."""
        import sqlite3

        from formaltask.tasks.lifecycle import transition_task_status

        result = transition_task_status(db_with_task, 42, "pending_review")

        assert result is True

        # Verify DB state
        with sqlite3.connect(db_with_task) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM tasks WHERE id = 42")
            status = cursor.fetchone()[0]

        assert status == "pending_review"

    def test_transition_to_blocked_user(self, db_with_task):
        """Task can transition from in_progress to blocked_user."""
        import sqlite3

        from formaltask.tasks.lifecycle import transition_task_status

        result = transition_task_status(db_with_task, 42, "blocked_user")

        assert result is True

        # Verify DB state
        with sqlite3.connect(db_with_task) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM tasks WHERE id = 42")
            status = cursor.fetchone()[0]

        assert status == "blocked_user"
