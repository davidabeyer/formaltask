"""Tests for worker spawning session launch behavior."""


def test_spawn_tmux_session_uses_cmux_adapter(monkeypatch, tmp_path):
    from formaltask.workers import spawner

    calls = []

    def fake_kill_session(name):
        calls.append(("kill", name))
        return True

    def fake_create_session(name, cwd, env_vars=None):
        calls.append(("create", name, cwd, env_vars))
        return True

    def fake_send_keys(name, keys):
        calls.append(("send", name, keys))
        return True

    def fail_tmux_call(cmd, **_kwargs):
        if cmd and cmd[0] == "tmux":
            raise AssertionError(f"unexpected tmux call: {cmd}")

    monkeypatch.setattr(spawner.cmux, "kill_session", fake_kill_session)
    monkeypatch.setattr(spawner.cmux, "create_session", fake_create_session)
    monkeypatch.setattr(spawner.cmux, "send_keys", fake_send_keys)
    monkeypatch.setattr(spawner.subprocess, "run", fail_tmux_call)
    monkeypatch.setattr(spawner.os, "getpid", lambda: 4242)
    monkeypatch.setattr(spawner, "get_claude_home", lambda: tmp_path)

    pid = spawner.spawn_tmux_session(
        task_id=123,
        worktree_path=str(tmp_path / "task-123"),
        session_id="session-123",
        project_root="/repo",
    )

    assert pid == 4242
    assert calls[0] == ("kill", "task-123")
    assert calls[1] == ("create", "task-123", str(tmp_path / "task-123"), {"PROJECT_ROOT": "/repo"})
    assert calls[2][0:2] == ("send", "task-123")
    assert "claude --permission-mode bypassPermissions --session-id session-123" in calls[2][2]


def test_spawn_tmux_session_raises_when_cmux_send_fails(monkeypatch, tmp_path):
    from formaltask.workers import spawner

    killed = []

    monkeypatch.setattr(spawner.cmux, "kill_session", lambda name: killed.append(name) or True)
    monkeypatch.setattr(spawner.cmux, "create_session", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(spawner.cmux, "send_keys", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(spawner, "get_claude_home", lambda: tmp_path)

    try:
        spawner.spawn_tmux_session(
            task_id=123,
            worktree_path=str(tmp_path / "task-123"),
            session_id="session-123",
            project_root="/repo",
        )
    except spawner.SpawnError as error:
        assert "send_keys failed" in str(error)
    else:
        raise AssertionError("expected SpawnError")

    assert killed == ["task-123", "task-123"]
