"""SessionEnd phase functions.

Plain functions for session-end hook (Task #2583).
No phase_engine dependency - simple list + loop pattern.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from hooks.pre_compact.skill_queue_flush import skill_queue_flush as _skill_queue_flush
from hooks.session_end.phases.index_conversation import index_conversation
from hooks.session_end.phases.vault_capture import vault_capture

logger = logging.getLogger(__name__)

_life_root = str(Path.home() / "life")
if _life_root not in sys.path:
    sys.path.insert(0, _life_root)


def run_skill_queue_flush(ctx: dict) -> None:
    """Run skill_queue_flush at session end too (not just precompact).

    SessionEnd ctx has session_id but not transcript_path.
    Find the transcript and inject it into ctx for the shared function.
    """
    session_id = ctx.get("session_id")
    if not session_id:
        return

    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.is_dir():
        return

    for f in projects_dir.rglob(f"{session_id}.jsonl"):
        enriched = {**ctx, "transcript_path": str(f)}
        _skill_queue_flush(enriched)
        return


def close_active_skill_session(ctx: dict) -> None:
    """Complete any open spans when conversation ends.

    Catches the case where no skill switch triggered step_logger's close logic.
    Scoped by session_id to avoid killing other sessions' spans.
    Completes both active AND suspended spans — suspended spans would otherwise
    be orphaned forever if the session ends while a different skill is active.
    Fails open — if DB is unavailable, does nothing.
    """
    session_id = ctx.get("session_id")
    if not session_id:
        return

    try:
        from db.connection import open_db
        from db.event import emit_event

        with open_db() as db:
            row = db.execute(
                "SELECT skill FROM skill_span "
                "WHERE status IN ('active', 'suspended') AND session_id = ? "
                "ORDER BY started_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()

            if row and row["skill"]:
                emit_event(row["skill"], "session_end", event_type="session_end")

            db.execute(
                "UPDATE skill_span SET status = 'completed', "
                "completed_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') "
                "WHERE status IN ('active', 'suspended') AND session_id = ?",
                (session_id,),
            )
            db.commit()

    except Exception as e:
        logger.debug("skill_session_close: failed (non-blocking): %s", e)


# Ordered list of phases (for runner to iterate)
PHASES = [
    close_active_skill_session,
    run_skill_queue_flush,
    index_conversation,
    vault_capture,
]

__all__ = [
    "close_active_skill_session",
    "run_skill_queue_flush",
    "index_conversation",
    "vault_capture",
    "PHASES",
]
