"""SessionStart phase functions.

Plain functions for session-start hook (Task #2582).
No phase_engine dependency - simple list + loop pattern.
"""

import fcntl
import json
import logging
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

from hooks.session_start import (
    auto_index_codebase,
    formaltask_db_location_hint,
    task_context_loader,
)

logger = logging.getLogger(__name__)

# File for SkillRun.create() to read current session_id
CURRENT_SESSION_FILE = Path.home() / ".claude" / "tmp" / "current-session.json"
BREADCRUMBS_FILE = Path.home() / ".claude" / "tmp" / "active-skills.json"
CARRY_FORWARD_FILE = Path.home() / ".claude" / "tmp" / "compacting-session.json"
STALE_THRESHOLD = timedelta(hours=24)
CARRY_FORWARD_MAX_AGE = timedelta(minutes=2)


def run_prune_stale_breadcrumbs(ctx: dict) -> None:
    """Remove skill breadcrumbs older than 24 hours.

    Priority 0 (runs first). Prevents stale breadcrumbs from accumulating
    across sessions and triggering contract validation for long-dead skills.
    """
    if not BREADCRUMBS_FILE.exists():
        return

    lock_path = BREADCRUMBS_FILE.with_suffix(".lock")
    try:
        with open(lock_path, "w") as lock_fd:
            # Non-blocking lock with retry (fail open after 2s)
            for _attempt in range(20):
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    import time

                    time.sleep(0.1)
            else:
                logger.debug("Failed to acquire breadcrumbs lock after 2s, skipping")
                return
            raw = json.loads(BREADCRUMBS_FILE.read_text())
            if not isinstance(raw, list):
                return

            cutoff = datetime.now(UTC) - STALE_THRESHOLD
            kept = []
            pruned = 0
            for entry in raw:
                ts = entry.get("timestamp", "")
                try:
                    entry_time = datetime.fromisoformat(ts)
                    if entry_time >= cutoff:
                        kept.append(entry)
                    else:
                        pruned += 1
                except (ValueError, TypeError):
                    logger.debug("Dropping breadcrumb with unparseable timestamp: %s", ts)
                    pruned += 1

            if pruned:
                BREADCRUMBS_FILE.write_text(json.dumps(kept, indent=2))
                logger.debug("Pruned %d stale breadcrumbs", pruned)
    except (json.JSONDecodeError, OSError) as e:
        logger.debug("Breadcrumb cleanup failed: %s", e)


def run_adopt_compacted_breadcrumbs(
    ctx: dict,
    *,
    breadcrumbs_file: Path = BREADCRUMBS_FILE,
    carry_file: Path = CARRY_FORWARD_FILE,
) -> None:
    """Re-tag orphaned breadcrumbs and skill_spans from a compacted session.

    Priority 0. PreCompact writes compacting-session.json with the old
    session_id. This phase reads it, re-tags matching breadcrumbs and
    skill_span DB rows with the new session_id, and deletes the carry-forward file.
    """
    if not carry_file.exists():
        return

    try:
        carry_data = json.loads(carry_file.read_text())
    except (json.JSONDecodeError, OSError):
        carry_file.unlink(missing_ok=True)
        return

    old_session_id = carry_data.get("old_session_id")
    new_session_id = ctx.get("session_id")
    timestamp_str = carry_data.get("timestamp", "")

    # Always clean up the carry-forward file
    carry_file.unlink(missing_ok=True)

    if not old_session_id or not new_session_id:
        return

    # Ignore stale carry-forward files (> 2 min = not from this compaction)
    try:
        carry_time = datetime.fromisoformat(timestamp_str)
        if datetime.now(UTC) - carry_time > CARRY_FORWARD_MAX_AGE:
            logger.debug("Stale carry-forward file (age > 2min), ignoring")
            return
    except (ValueError, TypeError):
        return

    # Re-tag skill_span rows in life.db
    try:
        from db.connection import open_db

        with open_db() as db:
            cursor = db.execute(
                "UPDATE skill_span SET session_id = ? "
                "WHERE session_id = ? AND status IN ('active', 'suspended')",
                (new_session_id, old_session_id),
            )
            if cursor.rowcount:
                db.commit()
                logger.debug("Adopted %d skill_spans from compacted session", cursor.rowcount)
    except Exception as e:
        logger.debug("skill_span adoption failed: %s", e)

    # Re-tag breadcrumbs in JSON file
    if not breadcrumbs_file.exists():
        return

    lock_path = breadcrumbs_file.with_suffix(".lock")
    try:
        with open(lock_path, "w") as lock_fd:
            # Non-blocking lock with retry (fail open after 2s)
            for _attempt in range(20):
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    import time

                    time.sleep(0.1)
            else:
                logger.debug("Failed to acquire breadcrumbs lock after 2s, skipping")
                return
            raw = json.loads(breadcrumbs_file.read_text())
            if not isinstance(raw, list):
                return

            adopted = 0
            for entry in raw:
                if entry.get("session_id") == old_session_id:
                    entry["session_id"] = new_session_id
                    adopted += 1

            if adopted:
                breadcrumbs_file.write_text(json.dumps(raw, indent=2))
                logger.debug("Adopted %d breadcrumbs from compacted session", adopted)
    except (json.JSONDecodeError, OSError) as e:
        logger.debug("Breadcrumb adoption failed: %s", e)


def run_write_session_id(ctx: dict) -> None:
    """Write session_id and transcript_path for SkillRun.create() to read.

    Priority 0 (runs first). Enables session-scoped skill breadcrumbs.
    transcript_path is the stable per-conversation identifier (unique file per session).
    """
    session_id = ctx.get("session_id")
    transcript_path = ctx.get("transcript_path")
    if session_id:
        CURRENT_SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {"session_id": session_id}
        if transcript_path:
            data["transcript_path"] = transcript_path
        CURRENT_SESSION_FILE.write_text(json.dumps(data))


def run_session_file(
    ctx: dict,
    *,
    projects_dir: Path | None = None,
    handoff_dir: Path | None = None,
) -> dict | None:
    """Load handoff context for worktree sessions or compaction resumption.

    Priority 1. Detection order:
    1. .session/name file in cwd → use thread name directly (worktree sessions)
    2. Breadcrumb via project_id (for compaction resumption)

    Args:
        ctx: Hook context with cwd and optional project_id.
        projects_dir: Base directory for project files (for testing).
        handoff_dir: Base directory for handoffs (for testing).

    Returns:
        Dict with hookSpecificOutput.additionalContext, or None if not found.
    """
    from hooks.pre_compact.handoff_writer import (
        HANDOFF_DIR,
        PROJECTS_DIR,
        find_prev_handoff,
    )

    if projects_dir is None:
        projects_dir = PROJECTS_DIR
    if handoff_dir is None:
        handoff_dir = HANDOFF_DIR

    # Check for session worktree first (.session/name takes priority)
    cwd = ctx.get("cwd", "")
    if cwd:
        session_name_file = Path(cwd) / ".session" / "name"
        if session_name_file.exists():
            thread_name = session_name_file.read_text().strip()
            prev_path = find_prev_handoff(thread_name, handoff_dir=handoff_dir)
            if prev_path:
                handoff_file = handoff_dir / prev_path
                if handoff_file.exists():
                    content = handoff_file.read_text()
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": "SessionStart",
                            "additionalContext": f"## Previous Handoff ({thread_name})\n\n{content}",
                        }
                    }

    # Fallback: Breadcrumb-based loading (for compaction resumption)
    project_id = ctx.get("project_id")
    if not project_id:
        return None

    breadcrumb = projects_dir / project_id / "handoff-thread.txt"
    if not breadcrumb.exists():
        return None

    thread_name = breadcrumb.read_text().strip()
    prev_path = find_prev_handoff(thread_name, handoff_dir=handoff_dir)
    if not prev_path:
        return None

    handoff_file = handoff_dir / prev_path
    if not handoff_file.exists():
        return None

    handoff_content = handoff_file.read_text()
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"## Previous Handoff ({thread_name})\n\n{handoff_content}",
        }
    }


def run_tdd_guard_init(ctx: dict) -> None:
    """Initialize TDD guard for the session.

    Priority 1. Runs tdd-guard init command.
    """
    cwd = ctx.get("cwd", ".")
    script_path = (
        Path(__file__).parent.parent.parent.parent / "scripts" / "setup-worktree-tdd-guard.sh"
    )
    if script_path.exists():
        try:
            subprocess.run([str(script_path), cwd], capture_output=True, timeout=30)
        except subprocess.TimeoutExpired:
            logger.warning("TDD guard init timed out")
        except Exception as e:
            logger.debug("TDD guard init failed: %s", e)


def run_auto_index(ctx: dict) -> None:
    """Trigger incremental codebase re-indexing.

    Priority 2 (can be slower).
    """
    auto_index_codebase.process(ctx)


def run_task_context(ctx: dict) -> dict | None:
    """Load task context for worktree agents.

    Priority 2. Loads task context and formats for agent injection.
    Returns hookSpecificOutput dict for runner to output to stdout.
    """
    return task_context_loader.process(ctx)


def run_db_location_hint(ctx: dict) -> None:
    """Warn about FormalTask database location in worktrees.

    Priority 2.
    """
    formaltask_db_location_hint.process(ctx)


# Ordered list of phases by priority (for runner to iterate)
PHASES = [
    # Priority 0
    run_prune_stale_breadcrumbs,  # Clean stale breadcrumbs before anything else
    run_adopt_compacted_breadcrumbs,  # Re-tag breadcrumbs from compacted session
    run_write_session_id,  # Must run first for skill breadcrumbs
    # Priority 1
    run_session_file,
    run_tdd_guard_init,
    # Priority 2
    run_auto_index,
    run_task_context,
    run_db_location_hint,
]

__all__ = [
    "run_prune_stale_breadcrumbs",
    "run_adopt_compacted_breadcrumbs",
    "run_write_session_id",
    "run_session_file",
    "run_tdd_guard_init",
    "run_auto_index",
    "run_task_context",
    "run_db_location_hint",
    "PHASES",
]
