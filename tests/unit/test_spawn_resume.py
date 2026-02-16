"""Test _check_resumable_session for respawn resume detection."""

import uuid

from formaltask.workers.spawner import _check_resumable_session


class TestCheckResumableSession:
    """Test _check_resumable_session returns session_id or None."""

    def _setup_worktree(self, tmp_path):
        """Create minimal worktree with .task/ directory."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        (worktree / ".task").mkdir()
        return worktree

    def _setup_claude_projects(self, tmp_path, worktree, session_id):
        """Create Claude session .jsonl file at the expected path."""
        project_path = str(worktree.resolve()).replace("/", "-").replace(".", "-")
        project_dir = tmp_path / "claude_home" / "projects" / project_path
        project_dir.mkdir(parents=True)
        (project_dir / f"{session_id}.jsonl").write_text("{}")

    def test_no_session_id_file_returns_none(self, tmp_path):
        """No .task/session_id file → None."""
        worktree = self._setup_worktree(tmp_path)

        result = _check_resumable_session(42, worktree)

        assert result is None

    def test_invalid_uuid_returns_none(self, tmp_path):
        """Invalid UUID in .task/session_id → None."""
        worktree = self._setup_worktree(tmp_path)
        (worktree / ".task" / "session_id").write_text("not-a-uuid")

        result = _check_resumable_session(42, worktree)

        assert result is None

    def test_empty_session_id_returns_none(self, tmp_path):
        """Empty .task/session_id → None."""
        worktree = self._setup_worktree(tmp_path)
        (worktree / ".task" / "session_id").write_text("")

        result = _check_resumable_session(42, worktree)

        assert result is None

    def test_valid_uuid_no_jsonl_returns_none(self, tmp_path, monkeypatch):
        """Valid UUID but no .jsonl session file → None."""
        worktree = self._setup_worktree(tmp_path)
        session_id = str(uuid.uuid4())
        (worktree / ".task" / "session_id").write_text(session_id)

        # Point get_claude_home to tmp_path so verify_session_exists looks there
        claude_home = tmp_path / "claude_home"
        claude_home.mkdir(exist_ok=True)
        monkeypatch.setattr("formaltask.workers.resume.get_claude_home", lambda: claude_home)

        result = _check_resumable_session(42, worktree)

        assert result is None

    def test_valid_uuid_with_jsonl_returns_session_id(self, tmp_path, monkeypatch):
        """Valid UUID with existing .jsonl → returns session_id."""
        worktree = self._setup_worktree(tmp_path)
        session_id = str(uuid.uuid4())
        (worktree / ".task" / "session_id").write_text(session_id)

        # Create the .jsonl file where verify_session_exists looks
        claude_home = tmp_path / "claude_home"
        monkeypatch.setattr("formaltask.workers.resume.get_claude_home", lambda: claude_home)
        self._setup_claude_projects(tmp_path, worktree, session_id)

        result = _check_resumable_session(42, worktree)

        assert result == session_id
