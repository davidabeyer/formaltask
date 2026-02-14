"""Test stale git lock cleanup."""

import os
import time

from formaltask.workers.spawner import (
    STALE_LOCK_SECONDS,
    _cleanup_stale_git_locks,
    _get_git_dir,
)


class TestGetGitDir:
    """Test _get_git_dir resolution."""

    def test_normal_repo_returns_git_directory(self, tmp_path):
        """Normal repo with .git directory returns that directory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        result = _get_git_dir(str(tmp_path))

        assert result == git_dir

    def test_worktree_follows_gitdir_pointer(self, tmp_path):
        """Worktree .git file containing gitdir: pointer is followed."""
        # Simulate worktree structure
        actual_git_dir = tmp_path / "main" / ".git" / "worktrees" / "task-123"
        actual_git_dir.mkdir(parents=True)

        worktree = tmp_path / "worktree"
        worktree.mkdir()
        git_file = worktree / ".git"
        git_file.write_text(f"gitdir: {actual_git_dir}")

        result = _get_git_dir(str(worktree))

        assert result == actual_git_dir

    def test_no_git_returns_none(self, tmp_path):
        """Path without .git returns None."""
        result = _get_git_dir(str(tmp_path))
        assert result is None


class TestCleanupStaleGitLocks:
    """Test _cleanup_stale_git_locks."""

    def test_removes_stale_lock_normal_repo(self, tmp_path):
        """Stale lock in normal repo is removed."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        lock_file = git_dir / "index.lock"
        lock_file.touch()
        # Make it stale
        old_time = time.time() - STALE_LOCK_SECONDS - 60
        os.utime(lock_file, (old_time, old_time))

        _cleanup_stale_git_locks(str(tmp_path))

        assert not lock_file.exists()

    def test_removes_stale_lock_worktree(self, tmp_path):
        """Stale lock in worktree is removed at correct location."""
        # Simulate worktree structure
        actual_git_dir = tmp_path / "main" / ".git" / "worktrees" / "task-456"
        actual_git_dir.mkdir(parents=True)
        lock_file = actual_git_dir / "index.lock"
        lock_file.touch()
        # Make it stale
        old_time = time.time() - STALE_LOCK_SECONDS - 60
        os.utime(lock_file, (old_time, old_time))

        worktree = tmp_path / "worktree"
        worktree.mkdir()
        (worktree / ".git").write_text(f"gitdir: {actual_git_dir}")

        _cleanup_stale_git_locks(str(worktree))

        assert not lock_file.exists()

    def test_preserves_fresh_lock(self, tmp_path):
        """Fresh lock (recent mtime) is NOT removed."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        lock_file = git_dir / "index.lock"
        lock_file.touch()  # Fresh lock

        _cleanup_stale_git_locks(str(tmp_path))

        assert lock_file.exists()  # Should NOT be removed

    def test_noop_when_no_lock(self, tmp_path):
        """No error when lock doesn't exist."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        _cleanup_stale_git_locks(str(tmp_path))  # Should not raise

    def test_noop_when_no_git_dir(self, tmp_path):
        """No error when .git doesn't exist."""
        _cleanup_stale_git_locks(str(tmp_path))  # Should not raise
