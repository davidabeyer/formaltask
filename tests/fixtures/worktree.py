"""Worktree fixtures for testing (Task #1655).

Provides fixtures for testing worktree and session directory operations:
- session_dir: Creates .claude/session/ directory structure
- worktree_root: Creates worktrees parent directory

Note: tmp_path is a pytest built-in - NOT extracted here.
"""

import pytest


@pytest.fixture
def session_dir(tmp_path):
    """Create session directory structure for testing.

    Creates a temporary directory structure matching the .claude/session/
    layout used by Claude Code for session metadata storage.

    Returns:
        pathlib.Path: Path to the session directory.

    Usage:
        def test_session_operations(session_dir):
            metadata_file = session_dir / "metadata.json"
            metadata_file.write_text('{"session_id": "test"}')
    """
    session_path = tmp_path / ".claude" / "session"
    session_path.mkdir(parents=True, exist_ok=True)
    return session_path


@pytest.fixture
def worktree_root(tmp_path):
    """Create worktrees root directory for testing.

    Creates a temporary directory for git worktrees, matching the
    ~/.claude/worktrees/ structure used for parallel task workers.

    Returns:
        pathlib.Path: Path to the worktrees root directory.

    Usage:
        def test_parallel_workers(worktree_root):
            task_worktree = worktree_root / "task-42"
            task_worktree.mkdir()
    """
    worktrees_path = tmp_path / ".claude" / "worktrees"
    worktrees_path.mkdir(parents=True, exist_ok=True)
    return worktrees_path
