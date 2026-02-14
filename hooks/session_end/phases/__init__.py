"""SessionEnd phase functions.

Plain functions for session-end hook (Task #2583).
No phase_engine dependency - simple list + loop pattern.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from hooks.pre_compact.skill_queue_flush import skill_queue_flush as _skill_queue_flush
from hooks.session_end.phases.index_conversation import index_conversation
from hooks.session_end.phases.vault_capture import vault_capture

logger = logging.getLogger(__name__)

_life_root = str(Path.home() / "life")
if _life_root not in sys.path:
    sys.path.insert(0, _life_root)


def run_doc_analyzer(ctx: dict) -> None:
    """Analyze session commits for documentation updates.

    Delegates to the existing doc_analyzer_worker logic
    for backward compatibility. Handles graceful degradation when
    the API key is not set.

    Args:
        ctx: Context dict with session_id, start_time, cwd fields
    """
    session_id = ctx.get("session_id")
    if not session_id:
        return

    # Check for API key early (graceful degradation)
    if not os.getenv("OPENROUTER_API_KEY"):
        logger.debug("OPENROUTER_API_KEY not set, skipping doc analysis")
        return

    try:
        # Import the worker logic
        from hooks.session_end.doc_analyzer_worker import (
            analyze_commits as _analyze_commits,
        )
        from hooks.session_end.doc_analyzer_worker import (
            filter_documented_files,
            get_openrouter_client,
            get_session_commits,
            load_analyzed_commits,
            save_analyzed_commits,
            write_pending,
        )

        # Get OpenRouter client
        client, model = get_openrouter_client()
        if client is None:
            return

        # Setup pending directory
        project_root = os.getenv("PROJECT_ROOT", ctx.get("cwd", os.getcwd()))
        pending_dir = Path(project_root) / ".claude" / "doc-guard"

        # Get commits and filter to documented files
        start_time = ctx.get("start_time")
        commits = get_session_commits(start_time)

        # Filter out already-analyzed commits
        analyzed = load_analyzed_commits(pending_dir)
        commits = [c for c in commits if c["hash"] not in analyzed]

        if not commits:
            return

        documented_files = filter_documented_files(commits)
        if not documented_files:
            return

        # Analyze commits
        result = _analyze_commits(client, model, commits, documented_files)

        if result and result.needs_update:
            write_pending(result, session_id, pending_dir)
            save_analyzed_commits(pending_dir, [c["hash"] for c in commits])

    except Exception as e:
        # Fire-and-forget: log but don't fail
        logger.debug("Doc analysis error (non-fatal): %s", e)


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
    run_doc_analyzer,
    close_active_skill_session,
    run_skill_queue_flush,
    index_conversation,
    vault_capture,
]

__all__ = [
    "run_doc_analyzer",
    "close_active_skill_session",
    "run_skill_queue_flush",
    "index_conversation",
    "vault_capture",
    "PHASES",
]
