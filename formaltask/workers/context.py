"""Task context detection for worker sessions.

Detects task ID from:
1. TASK_ID env var (explicitly set via tmux -e at spawn time)
2. TMUX session name (if TMUX env var passed to hooks)
3. Working directory worktree path (fallback when env vars unavailable)
"""

import logging
import os
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "get_task_id_from_session",
]

# Pattern to match task-{id} session names
TASK_PATTERN = re.compile(r"^task-(\d+)$")

# Patterns to match legitimate worktree paths (in order of specificity):
# 1. Claude Code worktrees: ~/.claude/worktrees/task-{id}/...
# 2. Git sibling worktrees: ../task-{id}-{branch}/... (note the hyphen-suffix)
# Intentionally excludes ambiguous paths like /tmp/task-123/ to reduce false positives
WORKTREE_PATTERNS = [
    re.compile(
        r"[/\\]\.claude[/\\]worktrees[/\\]task-(\d+)(?:[/\\]|$)"
    ),  # .claude/worktrees/task-{id}
    re.compile(r"[/\\]task-(\d+)-[^/\\]+(?:[/\\]|$)"),  # task-{id}-{branch} sibling worktree
]


def get_task_id_from_session() -> int | None:
    """Get task ID from environment or worktree path.

    Detection order (most reliable first):
    1. TASK_ID env var (explicitly set via tmux -e flag at spawn time)
    2. TMUX session name (if TMUX env var passed to hooks)
    3. Working directory worktree path (fallback when env vars not available)

    Logs DEBUG message indicating which path succeeded, and WARNING if
    TASK_ID env and TMUX session name disagree (indicates potential mismatch).

    Returns:
        Task ID if in a task-{id} context, None otherwise.
    """
    # Collect results from all detection methods for mismatch detection
    env_task_id = _get_task_id_from_env()
    tmux_task_id = _get_task_id_from_tmux()
    worktree_task_id = _get_task_id_from_worktree()

    # Log mismatch warning if TASK_ID env and TMUX session disagree
    if env_task_id is not None and tmux_task_id is not None and env_task_id != tmux_task_id:
        logger.warning(
            "TASK_ID mismatch: env=%d, tmux_session=%d (using env)",
            env_task_id,
            tmux_task_id,
        )

    # Return in priority order with DEBUG logging
    if env_task_id is not None:
        logger.debug("Task ID %d detected via TASK_ID env var", env_task_id)
        return env_task_id

    if tmux_task_id is not None:
        logger.debug("Task ID %d detected via TMUX session name", tmux_task_id)
        return tmux_task_id

    if worktree_task_id is not None:
        logger.debug("Task ID %d detected via worktree path", worktree_task_id)
        return worktree_task_id

    logger.debug("No task ID detected from any source")
    return None


def _get_task_id_from_env() -> int | None:
    """Get task ID from TASK_ID environment variable.

    This is the most reliable method when workers are spawned with
    `tmux new-session -e TASK_ID=<id>` which explicitly passes the
    variable to the tmux session environment.
    """
    task_id_str = os.environ.get("TASK_ID")
    if task_id_str:
        try:
            return int(task_id_str)
        except ValueError:
            return None
    return None


def _get_task_id_from_tmux() -> int | None:
    """Get task ID from tmux session name."""
    if not os.environ.get("TMUX"):
        return None

    try:
        result = subprocess.run(
            ["tmux", "display-message", "-p", "#{session_name}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError):
        # OSError covers FileNotFoundError (tmux not installed),
        # PermissionError, and other I/O issues
        return None

    if result.returncode != 0:
        return None

    session_name = result.stdout.strip()
    match = TASK_PATTERN.match(session_name)
    if match:
        return int(match.group(1))
    return None


def _get_task_id_from_worktree() -> int | None:
    """Get task ID from worktree directory path.

    Checks if cwd matches known worktree patterns:
    - ~/.claude/worktrees/task-{id}/...
    - ../task-{id}-{branch}/... (git sibling worktrees)

    Uses specific patterns to avoid false positives from ambiguous paths.
    """
    try:
        cwd = str(Path.cwd())
    except OSError:
        return None

    for pattern in WORKTREE_PATTERNS:
        match = pattern.search(cwd)
        if match:
            return int(match.group(1))
    return None
