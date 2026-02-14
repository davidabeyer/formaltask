"""Completion check. Pure function over state dict (Task #2734)."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from formaltask.core.completion_state import fetch_completion_state
from formaltask.core.rules_builtin import BUILTIN_RULES, apply_completion_rules

if TYPE_CHECKING:
    from formaltask.git.github import PRInfo


@dataclass(frozen=True)
class CompletionCheck:
    allowed: bool
    phase: str
    reason: str | None
    pr_info: "PRInfo | None" = None


def check_completion(task_id: int, db_path: str | Path, *, lightweight: bool = False) -> CompletionCheck | None:
    """Check if task completion is allowed.

    Args:
        task_id: Task ID to check
        db_path: Path to the database
        lightweight: Skip expensive subprocess calls (for dashboard polling)
    """
    state = fetch_completion_state(task_id, Path(db_path) if isinstance(db_path, str) else db_path, lightweight=lightweight)
    if state is None:
        return None
    pr_info = state.get("pr_info")
    if state.get("closed"):
        return CompletionCheck(allowed=True, phase="done", reason=None, pr_info=pr_info)
    if state.get("blocked"):
        return CompletionCheck(allowed=False, phase="blocked", reason="Task blocked by user question", pr_info=pr_info)

    from formaltask.core.rules import Rule

    task_rules = [Rule(**r) for r in state.get("completion_rules", [])]
    phase, reason, allowed = apply_completion_rules(task_rules + BUILTIN_RULES, state)
    if phase is None:
        return CompletionCheck(allowed=True, phase="done", reason=None, pr_info=pr_info)
    return CompletionCheck(allowed=allowed, phase=phase, reason=reason, pr_info=pr_info)
