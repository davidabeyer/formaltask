"""Phase: Update Session Activity.

Task #2569: Plain function architecture (no phase_engine).
Updates last_activity_at for the session on each user prompt.
"""

from __future__ import annotations

import fcntl
import json
import time
from datetime import datetime
from pathlib import Path

from formaltask.utils.json import MAX_CONFIG_FILE_SIZE, read_json_with_limit

ACTIVE_SESSIONS = Path.home() / ".claude" / "active-sessions.json"


def _flock_exclusive(f) -> None:
    """Acquire exclusive lock with non-blocking retry (fail open after 2s)."""
    for _attempt in range(20):
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            time.sleep(0.1)
    raise BlockingIOError("Failed to acquire lock after 2s")


def check(ctx: dict) -> None:
    """Update last_activity_at for the session.

    Args:
        ctx: Context dict with session_id, prompt, cwd fields

    Returns:
        None - promptsubmit cannot produce output
    """
    session_id = ctx.get("session_id")
    if not session_id:
        return

    if not ACTIVE_SESSIONS.exists():
        return

    with open(ACTIVE_SESSIONS, "r+") as f:
        try:
            _flock_exclusive(f)
        except BlockingIOError:
            return  # Fail open — skip activity update if lock unavailable
        try:
            data = read_json_with_limit(f, max_size=MAX_CONFIG_FILE_SIZE)

            for session in data["sessions"]:
                if session["session_id"] == session_id:
                    session["last_activity_at"] = datetime.now().isoformat()
                    break

            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
