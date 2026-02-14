"""Tmux session operations for worker management.

Pure functions - no state, no classes. Each function:
- Takes explicit arguments
- Returns a value or None/False on error
- Handles its own timeout and exceptions
"""

import re
import subprocess

_TIMEOUT = 5


def session_exists(name: str) -> bool:
    """Check if a tmux session exists."""
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", name],
            capture_output=True,
            timeout=_TIMEOUT,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def kill_session(name: str) -> bool:
    """Kill a tmux session."""
    try:
        subprocess.run(
            ["tmux", "kill-session", "-t", name],
            check=True,
            capture_output=True,
            timeout=10,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def attach_session(name: str) -> bool:
    """Attach to a tmux session interactively (no timeout)."""
    try:
        result = subprocess.run(["tmux", "attach-session", "-t", name], check=False)
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False


def send_keys(name: str, keys: str) -> bool:
    """Send keys to a tmux session."""
    try:
        subprocess.run(
            ["tmux", "send-keys", "-t", name, keys, "Enter"],
            check=True,
            capture_output=True,
            timeout=10,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def is_pane_alive(name: str) -> bool:
    """Check if tmux pane process is running (not exited)."""
    try:
        result = subprocess.run(
            ["tmux", "list-panes", "-t", name, "-F", "#{pane_dead}"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
        return result.returncode == 0 and result.stdout.strip() == "0"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def capture_pane(name: str, lines: int = 100) -> str | None:
    """Capture pane content with scrollback."""
    try:
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", name, "-p", "-e", "-S", f"-{lines}"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
        return result.stdout if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def get_pane_command(name: str) -> str | None:
    """Get the current command running in a tmux pane."""
    try:
        result = subprocess.run(
            ["tmux", "display", "-t", name, "-p", "#{pane_current_command}"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
        return result.stdout.strip() or None if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def is_pane_dead(name: str) -> bool:
    """Check if a tmux session's pane has exited."""
    try:
        result = subprocess.run(
            ["tmux", "display", "-t", name, "-p", "#{pane_dead}"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
        return result.returncode == 0 and result.stdout.strip() == "1"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def get_tmux_version() -> tuple[int, int]:
    """Get tmux version as (major, minor) tuple.

    Task #2586: Detect tmux version for -e flag support (3.2+).

    Returns:
        Tuple of (major, minor) version numbers. Returns (0, 0) if detection fails.
    """
    try:
        result = subprocess.run(
            ["tmux", "-V"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
        if result.returncode == 0:
            # Parse "tmux 3.2a" or "tmux 3.1c" format
            match = re.search(r"tmux\s+(\d+)\.(\d+)", result.stdout)
            if match:
                return (int(match.group(1)), int(match.group(2)))
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return (0, 0)


def create_session(
    name: str,
    cwd: str,
    env_vars: dict[str, str] | None = None,
    timeout: int = 30,
) -> bool:
    """Create detached tmux session.

    Handles tmux version detection for -e flag (3.2+).
    Falls back to set-environment for older versions.

    Args:
        name: Session name.
        cwd: Working directory for the session.
        env_vars: Optional dict of environment variables to set.
        timeout: Timeout for subprocess calls (default 30s).

    Returns:
        True if session created successfully, False otherwise.
    """
    try:
        # Detect tmux version for -e flag support
        tmux_version = get_tmux_version()
        use_e_flag = tmux_version >= (3, 2)

        # Build new-session command
        cmd = [
            "tmux",
            "new-session",
            "-d",
            "-s",
            name,
            "-c",
            cwd,
        ]

        # Add env vars via -e flag if tmux 3.2+
        if env_vars and use_e_flag:
            for key, value in env_vars.items():
                cmd.extend(["-e", f"{key}={value}"])

        cmd.extend(["bash", "--norc", "--noprofile"])

        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if result.returncode != 0:
            return False

        # For tmux < 3.2, use set-environment as fallback
        if env_vars and not use_e_flag:
            for key, value in env_vars.items():
                set_result = subprocess.run(
                    ["tmux", "set-environment", "-t", name, key, value],
                    capture_output=True,
                    timeout=10,
                )
                if set_result.returncode != 0:
                    return False

        return True

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def is_task_session(name: str) -> bool:
    """Check if name matches task-{digits} pattern."""
    return bool(re.match(r"^task-\d+$", name))


def get_all_task_sessions() -> list[str]:
    """List all task-* tmux sessions, sorted by task ID."""
    try:
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
        if result.returncode != 0:
            return []
        sessions = [s for s in result.stdout.strip().split("\n") if is_task_session(s)]
        return sorted(sessions, key=lambda s: int(s[5:]))
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []
