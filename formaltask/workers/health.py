#!/usr/bin/env python3
"""Worker health: collect state from tmux, transcript, DB, and git."""

import logging
import sqlite3
import subprocess
import time

from formaltask.core.completion_check import check_completion
from formaltask.paths import task_worktree
from formaltask.state.manager import get_transcript_mtime
from formaltask.tmux import (
    capture_pane,
    get_pane_command,
    is_task_session,
)
from formaltask.tmux import session_exists as tmux_session_exists
from formaltask.utils.constants import FindingPriority

STALENESS_THRESHOLD = 120
RUNNING_STATES = frozenset({"working", "implementing", "ready", "blocked", "needs_fix", "needs_pr"})
SHELL_NAMES = frozenset({"zsh", "bash", "sh", "fish"})

logger = logging.getLogger(__name__)

__all__ = [
    "get_worker_state_dict",
]


def _get_worktree_path(task_id: int) -> str:
    """Get worktree path for a task, empty string if not exists."""
    try:
        worktree = task_worktree(task_id)
        return str(worktree) if worktree.exists() else ""
    except OSError:
        return ""


def _fetch_task_metadata_batch(task_ids: list[int], db_path: str) -> dict[int, dict]:
    """Batch fetch title, started_at, blocked_question for multiple tasks."""
    if not task_ids:
        return {}

    from formaltask.db.connection import DatabaseConnection

    result: dict[int, dict] = {}
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            placeholders = ",".join("?" * len(task_ids))
            cursor.execute(  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
                f"SELECT id, title, started_at, blocked_question, epic_name FROM tasks WHERE id IN ({placeholders})",  # noqa: S608
                task_ids,
            )
            for task_id, title, started_at, blocked_question, epic_name in cursor.fetchall():
                result[task_id] = {
                    "title": title,
                    "started_at": started_at,
                    "blocked_question": blocked_question,
                    "epic_name": epic_name,
                }
    except OSError as error:
        logger.debug("Database not available for batch metadata: %s", error)
    except sqlite3.Error as error:
        logger.warning("Database query failed in batch metadata: %s", error)
    return result


def get_worker_state_dict(  # noqa: C901
    task_id: int,
    session_name: str,
    db_path: str | None = None,
    metadata_cache: dict[int, dict] | None = None,
) -> dict:
    """Collect worker state from tmux, transcript, DB, and git."""
    worktree_path = _get_worktree_path(task_id)

    if not is_task_session(session_name):
        return {
            "task_id": task_id,
            "session_name": session_name,
            "title": "Unknown",
            "pane_output": None,
            "health_state": "unknown",
            "is_stale": False,
            "source": "pane_scrape",
            "pr_number": None,
            "pr_status": "none",
            "worktree_path": worktree_path,
            "commits_ahead": 0,
            "started_at": None,
            "reviews_required": 0,
            "reviews_completed": 0,
            "tmux_session_exists": False,
            "pending_question": None,
            "finding_counts": {
                FindingPriority.P0: 0,
                FindingPriority.P1: 0,
                FindingPriority.P2: 0,
                FindingPriority.P3: 0,
            },
        }

    pane_output = capture_pane(session_name)

    # Staleness from transcript mtime, overridden if subprocess running
    transcript_mtime = get_transcript_mtime(task_id, db_path=db_path)
    if transcript_mtime is not None:
        is_stale = (time.time() - transcript_mtime) > STALENESS_THRESHOLD
        source = "transcript_mtime"
    else:
        is_stale, source = False, "pane_scrape"

    if is_stale:
        pane_cmd = get_pane_command(session_name)
        if pane_cmd and pane_cmd not in SHELL_NAMES:
            is_stale, source = False, "pane_subprocess"

    # Phase + crash detection (lightweight=True: skip stale reviews + AC commands)
    completion = check_completion(task_id, db_path, lightweight=True) if db_path else None
    health_state = completion.phase if completion else "unknown"
    if health_state in RUNNING_STATES and not tmux_session_exists(session_name):
        health_state = "exited"

    # Metadata from cache or DB fallback
    title = "Unknown"
    started_at = None
    pending_question = None
    epic_name = None
    if metadata_cache and task_id in metadata_cache:
        cached = metadata_cache[task_id]
        title = cached.get("title", "Unknown")
        started_at = cached.get("started_at")
        pending_question = cached.get("blocked_question")
        epic_name = cached.get("epic_name")
    elif db_path:
        try:
            from formaltask.db.connection import DatabaseConnection

            with DatabaseConnection(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT title, started_at, blocked_question, epic_name FROM tasks WHERE id = ?",
                    (task_id,),
                )
                row = cursor.fetchone()
                if row:
                    title, started_at, pending_question, epic_name = (
                        row[0],
                        row[1],
                        row[2] or None,
                        row[3],
                    )
        except OSError as error:
            logger.debug("Database not available for worker health: %s", error)
        except sqlite3.Error as error:
            logger.warning("Database query failed in worker health: %s", error)

    # Reviews, findings, commits — best-effort
    reviews_required, reviews_completed, commits_ahead = 0, 0, 0
    finding_counts: dict[FindingPriority, int] = {
        FindingPriority.P0: 0,
        FindingPriority.P1: 0,
        FindingPriority.P2: 0,
        FindingPriority.P3: 0,
    }
    if db_path:
        try:
            from formaltask.git.status import get_reviews_status

            reviews_required, reviews_completed = get_reviews_status(task_id, db_path)
        except (sqlite3.Error, OSError) as error:
            logger.debug("Failed to get reviews status for task %d: %s", task_id, error)
        try:
            from formaltask.git.status import get_finding_counts

            finding_counts = get_finding_counts(task_id, db_path)
        except (ImportError, sqlite3.Error, OSError) as error:
            logger.debug("Failed to get finding_counts for task %d: %s", task_id, error)
    if worktree_path:
        try:
            from formaltask.git.status import get_commits_ahead_of_main

            commits_ahead = get_commits_ahead_of_main(worktree_path)
        except (subprocess.CalledProcessError, OSError) as error:
            logger.debug("Failed to get commits ahead for task %d: %s", task_id, error)

    # PR info from completion result
    pr_number, pr_status = None, "none"
    if completion is not None and completion.pr_info is not None:
        pr_number = completion.pr_info.number
        pr_status = completion.pr_info.state.lower()

    has_tmux_session = tmux_session_exists(session_name)

    # Title truncation removed (Task #2821) - let each consumer decide.
    # Sidebar uses SIDEBAR_TITLE_MAX, detail pane shows full title.

    return {
        "task_id": task_id,
        "session_name": session_name,
        "title": title,
        "pane_output": pane_output,
        "health_state": health_state,
        "is_stale": is_stale,
        "source": source,
        "pr_number": pr_number,
        "pr_status": pr_status,
        "worktree_path": worktree_path,
        "commits_ahead": commits_ahead,
        "started_at": started_at,
        "reviews_required": reviews_required,
        "reviews_completed": reviews_completed,
        "tmux_session_exists": has_tmux_session,
        "pending_question": pending_question,
        "finding_counts": finding_counts,
        "epic_name": epic_name,
    }
