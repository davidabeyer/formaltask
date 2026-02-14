"""Tests for watch daemon orchestration rules (Task #2878).

Tests for ORCHESTRATION_RULES and evaluate_orchestration_rules in orchestrator.
"""

import sqlite3
from unittest.mock import patch

import pytest


class TestEvaluateOrchestrationRules:
    """Tests for evaluate_orchestration_rules behavior."""

    @pytest.fixture(autouse=True)
    def clear_last_fired(self):
        """Clear the _last_fired dict before each test for isolation."""
        from formaltask.workers import orchestrator

        orchestrator._last_fired.clear()
        yield
        orchestrator._last_fired.clear()

    def test_queries_in_progress_and_blocked_tasks(self, tmp_path):
        """Should query tasks with status IN ('in_progress', 'blocked')."""
        from formaltask.core.rules import Rule
        from formaltask.workers.orchestrator import evaluate_orchestration_rules

        # Create test database with tasks
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("INSERT INTO tasks (id, status) VALUES (1, 'in_progress')")
        conn.execute("INSERT INTO tasks (id, status) VALUES (2, 'blocked')")
        conn.execute("INSERT INTO tasks (id, status) VALUES (3, 'open')")  # Should be skipped
        conn.execute("INSERT INTO tasks (id, status) VALUES (4, 'completed')")  # Should be skipped
        conn.commit()
        conn.close()

        # Use a rule that always matches to see which tasks are evaluated
        test_rules = [
            Rule(when="true", then="Test message", target="notify", priority=0, name="test")
        ]

        # Mock osascript to capture which tasks trigger notifications
        with patch("formaltask.workers.orchestrator.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            evaluate_orchestration_rules(db_path, test_rules)

            # Check that notifications were triggered for in_progress and blocked tasks
            assert mock_run.call_count == 2

    def test_builds_context_with_task_fields(self, tmp_path):
        """Should build context dict with id, status, duration, metadata."""
        from formaltask.core.rules import Rule
        from formaltask.workers.orchestrator import evaluate_orchestration_rules

        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            )
        """)
        # Insert task with known created_at for duration calculation
        # Use 'localtime' to match Python's datetime.now() which returns local time
        conn.execute(
            "INSERT INTO tasks (id, status, created_at) VALUES (1, 'in_progress', datetime('now', '-3700 seconds', 'localtime'))"
        )
        conn.commit()
        conn.close()

        # Rule that matches on duration > 3600 (1 hour)
        test_rules = [
            Rule(
                when="duration > 3600",
                then="Task #{{ task_id }} running {{ duration }}s",
                target="notify",
                priority=0,
                name="long_running",
            )
        ]

        with patch("formaltask.workers.orchestrator.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            evaluate_orchestration_rules(db_path, test_rules)

            # Should trigger notification since duration > 3600
            assert mock_run.call_count == 1

    def test_notify_action_triggers_osascript(self, tmp_path):
        """Notify target should trigger macOS notification via osascript."""
        from formaltask.core.rules import Rule
        from formaltask.workers.orchestrator import evaluate_orchestration_rules

        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("INSERT INTO tasks (id, status) VALUES (1, 'in_progress')")
        conn.commit()
        conn.close()

        test_rules = [
            Rule(when="true", then="Test notification", target="notify", priority=0, name="test")
        ]

        with patch("formaltask.workers.orchestrator.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            evaluate_orchestration_rules(db_path, test_rules)

            # Verify osascript was called with display notification
            assert mock_run.call_count == 1
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert cmd[0] == "osascript"
            assert "-e" in cmd
            assert "display notification" in cmd[-1]

    def test_duplicate_firing_prevention(self, tmp_path):
        """Should prevent duplicate rule firings for the same task."""
        from formaltask.core.rules import Rule
        from formaltask.workers.orchestrator import evaluate_orchestration_rules

        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("INSERT INTO tasks (id, status) VALUES (1, 'in_progress')")
        conn.commit()
        conn.close()

        test_rules = [
            Rule(when="true", then="Test notification", target="notify", priority=0, name="test")
        ]

        with patch("formaltask.workers.orchestrator.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0

            # First call should trigger notification
            evaluate_orchestration_rules(db_path, test_rules)
            assert mock_run.call_count == 1

            # Second call should NOT trigger again (duplicate prevention)
            evaluate_orchestration_rules(db_path, test_rules)
            assert mock_run.call_count == 1  # Still 1, not 2
