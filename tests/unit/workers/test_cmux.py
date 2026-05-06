import json
import shlex
import subprocess

from formaltask import cmux


def completed(stdout="", returncode=0):
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr="")


def test_cmux_create_session_spawns_workspace_and_records_uuid(monkeypatch, tmp_path):
    calls = []
    workspaces = {
        "workspaces": [
            {"name": "task-17", "ref": "workspace:3", "id": "UUID-17"},
        ]
    }

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[:2] == ["cmux", "new-workspace"]:
            return completed("OK workspace:3\n")
        if cmd[:3] == ["cmux", "rpc", "workspace.list"]:
            return completed(json.dumps(workspaces))
        raise AssertionError(cmd)

    monkeypatch.setattr(cmux, "_STATE_PATH", tmp_path / "cmux-task-map.json")
    monkeypatch.setattr(cmux.subprocess, "run", fake_run)

    assert cmux.create_session("task-17", "/repo", {"A": "1"}) is True

    assert calls[0] == [
        "cmux",
        "new-workspace",
        "--name",
        "task-17",
        "--cwd",
        "/repo",
        "--command",
        "export A=1; exec bash --norc --noprofile",
    ]
    assert json.loads((tmp_path / "cmux-task-map.json").read_text()) == {"task-17": "UUID-17"}


def test_cmux_create_session_escapes_environment_values(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[:2] == ["cmux", "new-workspace"]:
            return completed("OK workspace:8\n")
        if cmd[:3] == ["cmux", "rpc", "workspace.list"]:
            return completed(json.dumps({"workspaces": [{"name": "task-8", "ref": "workspace:8", "id": "UUID-8"}]}))
        raise AssertionError(cmd)

    monkeypatch.setattr(cmux, "_STATE_PATH", tmp_path / "cmux-task-map.json")
    monkeypatch.setattr(cmux.subprocess, "run", fake_run)

    assert cmux.create_session("task-8", "/repo", {"QUOTE": "a'b"}) is True

    assert "export QUOTE=" + shlex.quote("a'b") + "; exec bash --norc --noprofile" in calls[0]


def test_cmux_session_exists_uses_workspace_list(monkeypatch):
    monkeypatch.setattr(
        cmux.subprocess,
        "run",
        lambda cmd, **kwargs: completed(json.dumps({"workspaces": [{"name": "task-1", "id": "UUID-1"}]})),
    )

    assert cmux.session_exists("task-1") is True
    assert cmux.session_exists("task-2") is False


def test_cmux_kill_session_closes_resolved_workspace(monkeypatch, tmp_path):
    calls = []
    (tmp_path / "cmux-task-map.json").write_text(json.dumps({"task-4": "UUID-4"}))

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return completed()

    monkeypatch.setattr(cmux, "_STATE_PATH", tmp_path / "cmux-task-map.json")
    monkeypatch.setattr(cmux.subprocess, "run", fake_run)

    assert cmux.kill_session("task-4") is True
    assert calls == [["cmux", "close-workspace", "--workspace", "UUID-4"]]


def test_cmux_send_keys_sends_text_then_return(monkeypatch, tmp_path):
    calls = []
    (tmp_path / "cmux-task-map.json").write_text(json.dumps({"task-5": "UUID-5"}))

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return completed()

    monkeypatch.setattr(cmux, "_STATE_PATH", tmp_path / "cmux-task-map.json")
    monkeypatch.setattr(cmux.subprocess, "run", fake_run)

    assert cmux.send_keys("task-5", "ft task run 5") is True
    assert calls == [
        ["cmux", "send", "--workspace", "UUID-5", "ft task run 5"],
        ["cmux", "send-key", "--workspace", "UUID-5", "Return"],
    ]


def test_cmux_capture_pane_reads_screen(monkeypatch, tmp_path):
    calls = []
    (tmp_path / "cmux-task-map.json").write_text(json.dumps({"task-6": "UUID-6"}))

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return completed("screen text")

    monkeypatch.setattr(cmux, "_STATE_PATH", tmp_path / "cmux-task-map.json")
    monkeypatch.setattr(cmux.subprocess, "run", fake_run)

    assert cmux.capture_pane("task-6", lines=40) == "screen text"
    assert calls == [["cmux", "read-screen", "--workspace", "UUID-6", "--scrollback", "--lines", "40"]]


def test_cmux_is_pane_alive_checks_tree_tty_with_ps(monkeypatch, tmp_path):
    calls = []
    tree = {"windows": [{"workspaces": [{"ref": "UUID-7", "panes": [{"surfaces": [{"tty": "ttys007"}]}]}]}]}
    (tmp_path / "cmux-task-map.json").write_text(json.dumps({"task-7": "UUID-7"}))

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[:3] == ["cmux", "tree", "--json"]:
            return completed(json.dumps(tree))
        if cmd[:2] == ["ps", "-t"]:
            return completed("S\n")
        raise AssertionError(cmd)

    monkeypatch.setattr(cmux, "_STATE_PATH", tmp_path / "cmux-task-map.json")
    monkeypatch.setattr(cmux.subprocess, "run", fake_run)

    assert cmux.is_pane_alive("task-7") is True
    assert calls == [["cmux", "tree", "--json"], ["ps", "-t", "ttys007", "-o", "stat="]]


def test_cmux_is_pane_alive_returns_false_when_ps_finds_no_process(monkeypatch, tmp_path):
    tree = {"windows": [{"workspaces": [{"id": "UUID-9", "panes": [{"surfaces": [{"tty": "ttys009"}]}]}]}]}
    (tmp_path / "cmux-task-map.json").write_text(json.dumps({"task-9": "UUID-9"}))

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["cmux", "tree", "--json"]:
            return completed(json.dumps(tree))
        if cmd[:2] == ["ps", "-t"]:
            return completed("", returncode=1)
        raise AssertionError(cmd)

    monkeypatch.setattr(cmux, "_STATE_PATH", tmp_path / "cmux-task-map.json")
    monkeypatch.setattr(cmux.subprocess, "run", fake_run)

    assert cmux.is_pane_alive("task-9") is False


def test_cmux_get_all_task_sessions_discovers_sorted_task_workspaces(monkeypatch):
    workspaces = {
        "workspaces": [
            {"name": "task-10", "id": "UUID-10"},
            {"name": "notes", "id": "UUID-notes"},
            {"name": "task-2", "id": "UUID-2"},
        ]
    }
    monkeypatch.setattr(cmux.subprocess, "run", lambda cmd, **kwargs: completed(json.dumps(workspaces)))

    assert cmux.get_all_task_sessions() == ["task-2", "task-10"]
