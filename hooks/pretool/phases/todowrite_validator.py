"""TodoWrite validator phase - validates TodoWrite tool usage.

Ensures workers use workflow template (first call only).
Uses single source of truth from formaltask.workers.workflow_steps.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _log_to_task(task_dir: Path, message: str) -> None:
    """Append timestamped message to .task/todowrite_validator.log."""
    try:
        log_file = task_dir / "todowrite_validator.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    except OSError:
        pass  # Logging should never break the validator


def _get_task_dir_from_cwd(cwd: str | None) -> Path | None:
    """Get .task/ directory from hook input cwd. Single source of truth."""
    if not cwd:
        return None
    task_dir = Path(cwd) / ".task"
    if (task_dir / "id").is_file():
        return task_dir
    return None


def _has_reviews(task_dir: Path) -> bool:
    """Check if task has required_reviews configured."""
    metadata_file = task_dir / "metadata.json"
    if metadata_file.exists():
        try:
            metadata = json.loads(metadata_file.read_text())
            required_reviews = metadata.get("required_reviews")
            # Explicitly empty list means no reviews
            if required_reviews is not None and not required_reviews:
                return False
        except (json.JSONDecodeError, OSError):
            pass
    # Default: reviews required (backwards compatibility)
    return True


def _step_present(todos: list[dict], step: str) -> bool:
    """Check if any todo contains all words from the step name.

    antirez style: no regex, simple substring matching.
    "Capture learnings" -> check if any todo contains "capture" and "learning"
    """
    words = step.lower().split()
    return any(all(w in t.get("content", "").lower() for w in words) for t in todos)


def check(ctx: dict) -> dict | None:
    """Validate TodoWrite includes required workflow steps (workers only, once).

    Uses single source of truth from formaltask.workers.workflow_steps.

    Returns:
        None to allow, or {"decision": "block", "reason": str} to block.
    """
    if ctx.get("tool_name") != "TodoWrite":
        return None

    # Use hook input's cwd (single source of truth)
    task_dir = _get_task_dir_from_cwd(ctx.get("cwd"))
    if not task_dir:
        return None  # Not a worker

    # Log that we're in a worker context
    _log_to_task(task_dir, f"TodoWrite intercepted in worker (cwd={ctx.get('cwd')})")

    marker = task_dir / "workflow_validated"
    if marker.exists():
        _log_to_task(task_dir, "SKIP: workflow_validated marker exists, allowing")
        return None  # Already validated

    todos = ctx.get("tool_input", {}).get("todos", [])
    todo_contents = [t.get("content", "") for t in todos]
    _log_to_task(task_dir, f"First TodoWrite validation - {len(todos)} todos received:")
    for i, content in enumerate(todo_contents, 1):
        _log_to_task(task_dir, f"  [{i}] {content[:80]}{'...' if len(content) > 80 else ''}")

    # Single source of truth for required workflow steps
    from formaltask.workers.instructions import get_required_steps

    has_reviews = _has_reviews(task_dir)
    required_steps = get_required_steps(has_reviews)
    _log_to_task(task_dir, f"Required steps (has_reviews={has_reviews}): {required_steps}")

    # Check each step
    missing = []
    for step in required_steps:
        matched = _step_present(todos, step)
        _log_to_task(task_dir, f"  '{step}': {'✓ MATCHED' if matched else '✗ MISSING'}")
        if not matched:
            missing.append(step)

    if missing:
        reason = f"Missing required workflow steps: {missing}. Your TodoWrite must include these."
        _log_to_task(task_dir, f"BLOCKED: {reason}")
        return {
            "decision": "block",
            "reason": reason,
        }

    try:
        marker.touch(exist_ok=True)
        _log_to_task(task_dir, "SUCCESS: All steps matched, created workflow_validated marker")
    except OSError as e:
        logger.debug("Failed to create workflow marker %s: %s", marker, e)
        _log_to_task(task_dir, f"WARNING: Failed to create marker: {e}")
    return None
