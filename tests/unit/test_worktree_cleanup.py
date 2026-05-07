from formaltask.git import worktree


def test_cleanup_keeps_live_cmux_worker_worktree(monkeypatch, tmp_path):
    wt = tmp_path / "task-123"
    wt.mkdir()

    def fake_run(cmd, cwd=None, timeout=30):
        if cmd == ["git", "status", "--porcelain"]:
            return 0, "", ""
        if cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return 0, "task-123", ""
        if cmd == ["tmux", "has-session", "-t", "task-123"]:
            return 1, "", "no session"
        if cmd[:4] == ["gh", "pr", "list", "--head"] and "merged" in cmd:
            return 0, '[{"number": 45, "baseRefName": "master", "mergedAt": "2026-05-05T00:00:00Z"}]', ""
        if cmd[:4] == ["gh", "pr", "list", "--head"] and "open" in cmd:
            return 0, "[]", ""
        if cmd[:3] == ["git", "log", "origin/task-123..HEAD"]:
            return 0, "", ""
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(worktree, "_run", fake_run)
    monkeypatch.setattr(worktree.cmux, "session_exists", lambda name: name == "task-123")

    result = worktree.check_worktree_safety(str(wt))

    assert result["safe"] is False
    assert result["reason"] == "Active cmux session: task-123"
    assert result["checks"]["no_tmux"] is True
    assert result["checks"]["no_cmux"] is False


def test_cleanup_keeps_live_tmux_worker_worktree(monkeypatch, tmp_path):
    wt = tmp_path / "task-456"
    wt.mkdir()

    def fake_run(cmd, cwd=None, timeout=30):
        if cmd == ["git", "status", "--porcelain"]:
            return 0, "", ""
        if cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return 0, "task-456", ""
        if cmd == ["tmux", "has-session", "-t", "task-456"]:
            return 0, "", ""
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(worktree, "_run", fake_run)
    monkeypatch.setattr(worktree.cmux, "session_exists", lambda name: False)

    result = worktree.check_worktree_safety(str(wt))

    assert result["safe"] is False
    assert result["reason"] == "Active tmux session: task-456"
    assert result["checks"]["no_tmux"] is False
