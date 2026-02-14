"""Unit tests for task-complete branch detection (Task #2401).

Tests for auto-detecting master/main branch to skip review gates.
"""

import json
import subprocess as _subprocess_module
from unittest.mock import MagicMock, patch

import pytest


def _create_task_with_required_reviews(db_path):
    """Helper to create a task with required reviews but no reviews recorded."""
    from formaltask.db.connection import DatabaseConnection

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test", "2025-01-01T00:00:00Z"),
        )
        metadata = json.dumps({"required_reviews": ["code-quality"]})
        cursor.execute(
            """INSERT INTO tasks (epic_name, title, description, position, status,
               created_at, started_at, metadata)
               VALUES (?, ?, ?, 1, 'in_progress', ?, ?, ?)""",
            (
                "test-epic",
                "Test Task",
                "Test",
                "2025-01-01T00:00:00Z",
                "2025-01-01T00:00:00Z",
                metadata,
            ),
        )
        task_id = cursor.lastrowid
        # Add commit for evidence guard
        cursor.execute(
            "INSERT INTO commits (task_id, commit_hash, commit_message) VALUES (?, ?, ?)",
            (task_id, "abc123", "Test commit"),
        )
        conn.commit()
        return task_id


# Capture the original subprocess.run at import time (before any patching)
_original_subprocess_run = _subprocess_module.run


def _mock_subprocess_for_branch(branch_name: str | None):
    """Create a subprocess mock that returns branch_name for rev-parse --abbrev-ref.

    Args:
        branch_name: Branch name to return, or None for git failure
    """

    def subprocess_side_effect(args, **kwargs):
        # Only mock the branch detection call
        if args == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            mock_result = MagicMock()
            if branch_name is None:
                mock_result.returncode = 1
                mock_result.stdout = ""
            else:
                mock_result.returncode = 0
                mock_result.stdout = f"{branch_name}\n"
            return mock_result
        # For all other subprocess calls, use original function (captured before patching)
        return _original_subprocess_run(args, **kwargs)

    return subprocess_side_effect


class TestBranchDetectionSkipsReviews:
    """Tests for branch detection logic in task-complete."""

    @pytest.mark.parametrize("branch", ["master", "main"])
    def test_skips_reviews_on_default_branch(self, db_path, capsys, branch):
        """task-complete skips review gates when on default branch (master or main)."""
        from formaltask.cli.commands.task_complete import task_complete

        task_id = _create_task_with_required_reviews(db_path)

        # Mock only the branch detection subprocess call
        with (
            patch(
                "formaltask.cli.commands.task_complete.subprocess.run",
                side_effect=_mock_subprocess_for_branch(branch),
            ),
            patch("formaltask.git.utils.get_default_branch", return_value=branch),
        ):
            result = task_complete(
                task_id=task_id,
                db_path=db_path,
                no_evidence=False,
            )

        # Should succeed (skip review gates when on default branch)
        assert result == 0

        # Verify log message
        captured = capsys.readouterr()
        assert f"Skipping review gates (on {branch} branch)" in captured.out

    def test_requires_reviews_on_feature_branch(self, db_path):
        """task-complete requires reviews when on feature branch (e.g., task-123)."""
        from formaltask.cli.commands.task_complete import task_complete
        from formaltask.tasks.guards import GuardViolation

        task_id = _create_task_with_required_reviews(db_path)

        # Mock git to return feature branch name
        # Should raise GuardViolation due to missing reviews
        with (
            patch(
                "formaltask.cli.commands.task_complete.subprocess.run",
                side_effect=_mock_subprocess_for_branch("task-123"),
            ),
            patch("formaltask.git.utils.get_default_branch", return_value="master"),
            pytest.raises(GuardViolation) as exc_info,
        ):
            task_complete(
                task_id=task_id,
                db_path=db_path,
                no_evidence=False,
            )

        assert "review" in str(exc_info.value).lower()

    def test_detached_head_requires_reviews(self, db_path):
        """Detached HEAD state requires reviews (safe default)."""
        from formaltask.cli.commands.task_complete import task_complete
        from formaltask.tasks.guards import GuardViolation

        task_id = _create_task_with_required_reviews(db_path)

        # Mock git to return "HEAD" for detached HEAD state
        with (
            patch(
                "formaltask.cli.commands.task_complete.subprocess.run",
                side_effect=_mock_subprocess_for_branch("HEAD"),
            ),
            patch("formaltask.git.utils.get_default_branch", return_value="master"),
            pytest.raises(GuardViolation) as exc_info,
        ):
            task_complete(
                task_id=task_id,
                db_path=db_path,
                no_evidence=False,
            )

        assert "review" in str(exc_info.value).lower()

    def test_git_failure_requires_reviews(self, db_path):
        """Git failure requires reviews (safe default)."""
        from formaltask.cli.commands.task_complete import task_complete
        from formaltask.tasks.guards import GuardViolation

        task_id = _create_task_with_required_reviews(db_path)

        # Mock git to fail (branch_name=None triggers failure)
        with (
            patch(
                "formaltask.cli.commands.task_complete.subprocess.run",
                side_effect=_mock_subprocess_for_branch(None),
            ),
            patch("formaltask.git.utils.get_default_branch", return_value="master"),
            pytest.raises(GuardViolation) as exc_info,
        ):
            task_complete(
                task_id=task_id,
                db_path=db_path,
                no_evidence=False,
            )

        assert "review" in str(exc_info.value).lower()
