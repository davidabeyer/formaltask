"""SessionStart phase functions.

Plain functions for session-start hook.
No phase_engine dependency - simple list + loop pattern.
"""

import logging

from hooks.session_start import (
    formaltask_db_location_hint,
    task_context_loader,
)

logger = logging.getLogger(__name__)


def run_task_context(ctx: dict) -> dict | None:
    """Load task context for worktree agents.

    Loads task context and formats for agent injection.
    Returns hookSpecificOutput dict for runner to output to stdout.
    """
    return task_context_loader.process(ctx)


def run_db_location_hint(ctx: dict) -> None:
    """Warn about FormalTask database location in worktrees."""
    formaltask_db_location_hint.process(ctx)


PHASES = [
    run_task_context,
    run_db_location_hint,
]

__all__ = [
    "run_task_context",
    "run_db_location_hint",
    "PHASES",
]
