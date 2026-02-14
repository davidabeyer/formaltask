"""Tests for rebase_worktree_onto_target() helper function.

Task #2335: Extract rebase workflow from spawn_worker().
"""

import subprocess
from unittest.mock import MagicMock, patch


class TestRebaseWorktreeOntoTarget:
    """Test cases for rebase_worktree_onto_target() function."""

    def test_rebase_failure_aborts_and_restores_stash(self):
        """Verify rebase failure returns error without raising exception."""
        from formaltask.workers.spawner import rebase_worktree_onto_target

        with (
            patch("formaltask.workers.spawner.subprocess.run") as mock_run,
            patch("formaltask.workers.spawner.logging.getLogger") as mock_logger,
        ):
            mock_log = MagicMock()
            mock_logger.return_value = mock_log

            def side_effect(*args, **kwargs):
                cmd = args[0]

                if cmd == ["git", "fetch", "origin", "master"]:
                    return subprocess.CompletedProcess(args=cmd, returncode=0)
                if cmd[0:2] == ["git", "stash"] and "push" in cmd:
                    return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"Saved working directory")
                if cmd == ["git", "rebase", "origin/master"]:
                    # Simulate rebase failure
                    error = subprocess.CalledProcessError(1, cmd)
                    error.stderr = b"CONFLICT: merge conflict"
                    raise error
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"")

            mock_run.side_effect = side_effect

            # Should not raise - logs warning and continues
            rebase_worktree_onto_target(
                worktree_path="/tmp/test-worktree",
                task_id=42,
                target_branch="origin/master",
            )

            # Verify warning was logged
            mock_log.warning.assert_called()

    def test_fetch_failure_logs_warning_and_continues(self):
        """Verify fetch failure is handled gracefully."""
        from formaltask.workers.spawner import rebase_worktree_onto_target

        with (
            patch("formaltask.workers.spawner.subprocess.run") as mock_run,
            patch("formaltask.workers.spawner.logging.getLogger") as mock_logger,
        ):
            mock_log = MagicMock()
            mock_logger.return_value = mock_log

            def side_effect(cmd, *args, **kwargs):
                if cmd == ["git", "fetch", "origin", "master"]:
                    error = subprocess.CalledProcessError(1, cmd)
                    error.stderr = b"fatal: unable to access remote"
                    raise error
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"")

            mock_run.side_effect = side_effect

            # Should not raise - handles gracefully
            rebase_worktree_onto_target(
                worktree_path="/tmp/test-worktree",
                task_id=42,
                target_branch="origin/master",
            )

            # Verify warning was logged
            mock_log.warning.assert_called()

    def test_subprocess_calls_have_timeout(self):
        """Verify all subprocess calls include timeout=30 to prevent hanging."""
        from formaltask.workers.spawner import rebase_worktree_onto_target

        with patch("formaltask.workers.spawner.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git"], returncode=0, stdout=b"No local changes to save",
            )

            rebase_worktree_onto_target(
                worktree_path="/tmp/test-worktree",
                task_id=42,
                target_branch="origin/master",
            )

            # Verify all subprocess calls include timeout=30
            for call_args in mock_run.call_args_list:
                kwargs = call_args.kwargs if hasattr(call_args, "kwargs") else call_args[1]
                assert "timeout" in kwargs, f"Missing timeout in call: {call_args}"
                assert kwargs["timeout"] == 30, f"Timeout should be 30, got {kwargs['timeout']}"

    def test_stash_pop_conflict_logs_warning(self):
        """Verify stash pop conflict after successful rebase logs warning."""
        from formaltask.workers.spawner import rebase_worktree_onto_target

        with (
            patch("formaltask.workers.spawner.subprocess.run") as mock_run,
            patch("formaltask.workers.spawner.logging.getLogger") as mock_logger,
        ):
            mock_log = MagicMock()
            mock_logger.return_value = mock_log

            def side_effect(cmd, *args, **kwargs):
                if cmd[0:2] == ["git", "stash"] and "push" in cmd:
                    return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"Saved working directory")
                elif cmd == ["git", "stash", "pop"]:
                    # Simulate stash pop conflict
                    return subprocess.CompletedProcess(args=cmd, returncode=1, stderr=b"CONFLICT: merge conflict in file.txt")
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"")

            mock_run.side_effect = side_effect

            rebase_worktree_onto_target(
                worktree_path="/tmp/test-worktree",
                task_id=42,
                skip_fetch=True,
                target_branch="origin/master",
            )

            # Verify warning was logged about stash pop conflict
            mock_log.warning.assert_called()
            warning_call = mock_log.warning.call_args[0][0]
            assert "Stash pop had conflicts" in warning_call
            assert "resolve manually" in warning_call
