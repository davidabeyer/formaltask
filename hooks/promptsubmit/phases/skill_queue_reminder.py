"""Phase: Inject pending-queue reminder during skill sessions.

Queries the skill tracking database for an active or suspended skill_span
matching the current session. Checks suspended too so the reminder survives
skill nesting (e.g., /mode-verify invoked during another skill).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_life_root = str(Path.home() / "life")
if _life_root not in sys.path:
    sys.path.insert(0, _life_root)

QUEUE_SKILLS = {
    # Add skill queue entries here as needed:
    # "skill-name": {
    #     "path": "~/path/to/pending-queue.md",
    #     "arrows": "Type1/Type2",
    # },
}


def check(ctx: dict) -> dict | None:
    """Inject queue reminder if a skill session (active or suspended) has a pending-queue."""
    session_id = ctx.get("session_id")
    if not session_id:
        return None

    try:
        from db.connection import open_db

        with open_db() as db:
            row = db.execute(
                "SELECT skill FROM skill_span "
                "WHERE status IN ('active', 'suspended') AND session_id = ? "
                "ORDER BY started_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()

        if not row:
            return None

        skill = row["skill"]
        info = QUEUE_SKILLS.get(skill)
        if not info:
            return None

        reminder = (
            f"[Queue active: {info['path']}. "
            f"After confirmed moments, silently append: "
            f"timestamp + context + -> items ({info['arrows']}). Don't announce.]"
        )
        return {"context": reminder}

    except Exception as e:
        logger.debug("skill_queue_reminder: %s", e)
        return None
