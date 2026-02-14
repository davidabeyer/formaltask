"""Stop hook phases - completion enforcement."""

from __future__ import annotations

import json
import logging

from formaltask.db.connection import DatabaseConnection

logger = logging.getLogger(__name__)

TERMINAL = frozenset({"completed", "cancelled", "blocked_user"})
WAITING_TOOLS = frozenset({"AskUserQuestion"})


def _last_tool_was_waiting(transcript_path: str | None) -> bool:
    """Check if the last tool call was a waiting tool (e.g., AskUserQuestion)."""
    if not transcript_path:
        return False
    try:
        last_tool = None
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "tool_use":
                        last_tool = entry.get("name")
                except json.JSONDecodeError:
                    continue
        return last_tool in WAITING_TOOLS
    except OSError:
        return False


def check_completion(ctx: dict) -> dict | None:
    """Block stop unless task is in terminal status or waiting for user."""
    task_id, db_path = ctx.get("task_id"), ctx.get("db_path")
    if not task_id or not db_path or ctx.get("stop_hook_active"):
        return None
    if _last_tool_was_waiting(ctx.get("transcript_path")):
        return None

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        status = row[0] if row else None

    if status in TERMINAL or status is None:
        return None
    return {"decision": "block", "reason": f"Run: ft task complete {task_id}"}


PHASES = [check_completion]
