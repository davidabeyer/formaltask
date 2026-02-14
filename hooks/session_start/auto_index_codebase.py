#!/usr/bin/env python3
"""
Auto-index codebase SessionStart hook.

Triggers incremental re-indexing on session start. Uses a local timestamp
file to track last successful index, avoiding the need to query the MCP
server synchronously.
"""

import json
import subprocess
import sys
import time
from pathlib import Path


def load_claude_context_env() -> dict[str, str]:
    """Load claude-context environment variables from ~/.claude.json.

    Returns dict of env vars from mcpServers.claude-context.env, or empty dict
    if file doesn't exist or claude-context is not configured.
    """
    config_path = Path.home() / ".claude.json"
    if not config_path.exists():
        return {}

    try:
        config = json.loads(config_path.read_text())
        return config.get("mcpServers", {}).get("claude-context", {}).get("env", {})
    except (json.JSONDecodeError, OSError):
        return {}


# Directory for tracking reindex state (local, not cloud index)
STATE_DIR = Path.home() / ".claude" / "claude-context-state"

# Minimum hours between reindex attempts
MIN_REINDEX_INTERVAL_HOURS = 1


def get_last_index_time() -> float:
    """Get timestamp of last successful index.

    Returns 0.0 if never indexed or file doesn't exist.
    """
    timestamp_file = STATE_DIR / "last-index-timestamp"
    if not timestamp_file.exists():
        return 0.0

    try:
        return float(timestamp_file.read_text().strip())
    except (ValueError, OSError):
        return 0.0


def update_last_index_time() -> None:
    """Update last index timestamp to now."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp_file = STATE_DIR / "last-index-timestamp"
    timestamp_file.write_text(str(time.time()))


def should_reindex() -> bool:
    """Check if enough time has passed since last reindex.

    Returns True if:
    - Never indexed before
    - Last index was more than MIN_REINDEX_INTERVAL_HOURS ago
    """
    last_index = get_last_index_time()
    if last_index == 0.0:
        return True

    hours_since = (time.time() - last_index) / 3600
    return hours_since >= MIN_REINDEX_INTERVAL_HOURS


def is_worker_running() -> bool:
    """Check if a background reindex worker is already running.

    Returns True if reindex.lock exists and is not stale.
    Stale locks (>1 hour old) are auto-removed to prevent permanent blocking
    from crashed workers.
    """
    lock_file = STATE_DIR / "reindex.lock"
    if not lock_file.exists():
        return False

    # Auto-remove stale locks (>1 hour old)
    LOCK_TIMEOUT_SECONDS = 3600  # 1 hour
    try:
        lock_age = time.time() - lock_file.stat().st_mtime
        if lock_age > LOCK_TIMEOUT_SECONDS:
            lock_file.unlink(missing_ok=True)
            return False
    except OSError:
        # Lock file disappeared during check
        return False

    return True


def spawn_worker() -> bool:
    """Spawn a background reindex worker process.

    Creates a lock file and spawns a detached subprocess to perform reindexing.
    Returns True on success.

    Implements <!-- BACKGROUND-WORKERS --> from CLAUDE.md.
    """
    import os

    # Create lock file before spawning
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = STATE_DIR / "reindex.lock"
    lock_file.write_text("")

    # Get path to worker script (same directory as this module)
    _this_dir = os.path.dirname(os.path.abspath(__file__))
    worker_script = Path(_this_dir) / "auto_index_worker.py"

    # Spawn detached background process
    subprocess.Popen(
        [sys.executable, str(worker_script)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return True


def process(data: dict) -> dict:
    """Process hook data and return result.

    This function can be called directly by the dispatcher.

    Args:
        data: Hook input (unused for this handler).

    Returns:
        Empty dict (this handler doesn't produce output).
    """
    _ = data  # Not needed for this handler
    if not should_reindex():
        return {}

    if is_worker_running():
        return {}

    spawn_worker()
    return {}


def main() -> None:
    """SessionStart hook entry point (stdin-based).

    Triggers incremental reindex if enough time has passed since last index.
    The worker runs in background (fire-and-forget pattern).
    """
    process({})


if __name__ == "__main__":
    main()
