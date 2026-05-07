"""Cmux workspace operations for worker management."""

import json
import re
import shlex
import subprocess
from pathlib import Path

_TIMEOUT = 5
_STATE_PATH = Path.home() / ".claude" / "cmux-task-map.json"


def _run(cmd: list[str], timeout: int = _TIMEOUT) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _load_state() -> dict[str, str]:
    try:
        return json.loads(_STATE_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _save_state(state: dict[str, str]) -> None:
    try:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STATE_PATH.write_text(json.dumps(state, sort_keys=True))
    except OSError:
        pass


def _workspace_payload() -> list[dict]:
    try:
        result = _run(["cmux", "rpc", "workspace.list", "{}"])
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []
    if result.returncode != 0:
        return []
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return []
    if isinstance(payload, list):
        return payload
    workspaces = payload.get("workspaces", [])
    return workspaces if isinstance(workspaces, list) else []


def _workspace_ref(workspace: dict) -> str | None:
    for key in ("id", "ref", "uuid"):
        value = workspace.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _workspace_name(workspace: dict) -> str | None:
    value = workspace.get("name") or workspace.get("title")
    return value if isinstance(value, str) else None


def _find_workspace(name: str) -> dict | None:
    for workspace in _workspace_payload():
        if _workspace_name(workspace) == name:
            return workspace
    return None


def _resolve_workspace(name: str) -> str | None:
    state = _load_state()
    if name in state:
        return state[name]
    workspace = _find_workspace(name)
    if not workspace:
        return None
    ref = _workspace_ref(workspace)
    if ref:
        state[name] = ref
        _save_state(state)
    return ref


def _remember_workspace(name: str, ref: str | None) -> None:
    workspace = _find_workspace(name)
    durable_ref = _workspace_ref(workspace) if workspace else ref
    if not durable_ref:
        return
    state = _load_state()
    state[name] = durable_ref
    _save_state(state)


def _shell_exports(env_vars: dict[str, str] | None) -> str:
    exports = [f"export {key}={shlex.quote(value)}" for key, value in (env_vars or {}).items()]
    exports.append("exec bash --norc --noprofile")
    return "; ".join(exports)


def session_exists(name: str) -> bool:
    return _find_workspace(name) is not None


def kill_session(name: str) -> bool:
    workspace = _resolve_workspace(name)
    if not workspace:
        return False
    try:
        result = _run(["cmux", "close-workspace", "--workspace", workspace], timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def attach_session(name: str) -> bool:
    workspace = _resolve_workspace(name)
    if not workspace:
        return False
    try:
        result = subprocess.run(["cmux", "select-workspace", "--workspace", workspace], check=False)
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False


def send_keys(name: str, keys: str) -> bool:
    workspace = _resolve_workspace(name)
    if not workspace:
        return False
    try:
        send = _run(["cmux", "send", "--workspace", workspace, keys], timeout=10)
        if send.returncode != 0:
            return False
        enter = _run(["cmux", "send-key", "--workspace", workspace, "Return"], timeout=10)
        return enter.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _surfaces(node):
    if isinstance(node, dict):
        if "surfaces" in node and isinstance(node["surfaces"], list):
            yield from node["surfaces"]
        for value in node.values():
            yield from _surfaces(value)
    elif isinstance(node, list):
        for item in node:
            yield from _surfaces(item)


def _workspace_nodes(node, workspace: str):
    if isinstance(node, dict):
        if node.get("id") == workspace or node.get("ref") == workspace or node.get("name") == workspace:
            yield node
        for value in node.values():
            yield from _workspace_nodes(value, workspace)
    elif isinstance(node, list):
        for item in node:
            yield from _workspace_nodes(item, workspace)


def _workspace_ttys(workspace: str) -> list[str]:
    try:
        result = _run(["cmux", "tree", "--json"])
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []
    if result.returncode != 0:
        return []
    try:
        tree = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return []
    ttys: list[str] = []
    for workspace_node in _workspace_nodes(tree, workspace):
        for surface in _surfaces(workspace_node):
            tty = surface.get("tty") if isinstance(surface, dict) else None
            if isinstance(tty, str) and tty:
                ttys.append(tty)
    return ttys


def is_pane_alive(name: str) -> bool:
    workspace = _resolve_workspace(name)
    if not workspace:
        return False
    for tty in _workspace_ttys(workspace):
        try:
            result = _run(["ps", "-t", tty, "-o", "stat="])
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
        if result.returncode == 0 and result.stdout.strip():
            return True
    return False


def capture_pane(name: str, lines: int = 100) -> str | None:
    workspace = _resolve_workspace(name)
    if not workspace:
        return None
    try:
        result = _run(["cmux", "read-screen", "--workspace", workspace, "--scrollback", "--lines", str(lines)])
        return result.stdout if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def get_pane_command(name: str) -> str | None:
    return None


def is_pane_dead(name: str) -> bool:
    return not is_pane_alive(name)


def create_session(
    name: str,
    cwd: str,
    env_vars: dict[str, str] | None = None,
    timeout: int = 30,
) -> bool:
    try:
        result = _run(
            ["cmux", "new-workspace", "--name", name, "--cwd", cwd, "--command", _shell_exports(env_vars)],
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
    if result.returncode != 0:
        return False
    match = re.search(r"workspace:\d+", result.stdout or "")
    _remember_workspace(name, match.group(0) if match else None)
    return True


def is_task_session(name: str) -> bool:
    return bool(re.match(r"^task-\d+$", name))


def get_all_task_sessions() -> list[str]:
    sessions = [_workspace_name(workspace) for workspace in _workspace_payload()]
    tasks = [name for name in sessions if name and is_task_session(name)]
    return sorted(tasks, key=lambda name: int(name[5:]))
