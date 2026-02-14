"""Task lifecycle management - single source of truth for status transitions.

This module provides the centralized function for ALL task status transitions,
ensuring proper timestamp coordination and data integrity.

State Machine Diagram
=====================

::

                                 ┌───────────┐
                                 │   OPEN    │
                                 └─────┬─────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        ▼
        ┌───────────┐           ┌─────────────┐           ┌───────────┐
        │ CANCELLED │◄──────────│ IN_PROGRESS │──────────►│ DEFERRED  │
        └───────────┘           └──────┬──────┘           └─────┬─────┘
              ▲                        │                        │
              │         ┌──────────────┼──────────────┐         │
              │         │              │              │         │
              │         ▼              ▼              ▼         ▼
              │   ┌───────────┐  ┌───────────┐  ┌───────────┐   │
              ├───│  BLOCKED  │  │BLOCKED_USR│  │PEND_REVIEW│   │
              │   └─────┬─────┘  └─────┬─────┘  └─────┬─────┘   │
              │         │              │              │         │
              │         └──────────────┴──────────────┘         │
              │                        │                        │
              │                        ▼                        │
              │                 ┌─────────────┐                 │
              │                 │PENDING_MERGE│                 │
              │                 └──────┬──────┘                 │
              │                        │                        │
              │                        ▼                        │
              │                 ┌─────────────┐                 │
              └─────────────────│  COMPLETED  │◄────────────────┘
                                └─────────────┘

Valid Transitions:
    OPEN -> IN_PROGRESS, CANCELLED, DEFERRED
    IN_PROGRESS -> PENDING_MERGE, PENDING_REVIEW, BLOCKED_USER, BLOCKED, COMPLETED, DEFERRED, CANCELLED
    PENDING_MERGE -> COMPLETED, IN_PROGRESS, CANCELLED
    PENDING_REVIEW -> COMPLETED, IN_PROGRESS, CANCELLED
    BLOCKED_USER -> IN_PROGRESS, COMPLETED, CANCELLED
    BLOCKED -> IN_PROGRESS, CANCELLED, DEFERRED
    DEFERRED -> OPEN, CANCELLED
    COMPLETED -> (terminal state)
    CANCELLED -> (terminal state)

Functions:
    transition_task_status() - Transition a task to a new status with timestamp coordination

Example:
    >>> from formaltask.tasks.lifecycle import transition_task_status
    >>> # Start a task (with race protection)
    >>> success = transition_task_status(db_path, 42, 'in_progress', idempotent=True)
    >>> if not success:
    ...     print("Task already started by another process")
    >>>
    >>> # Complete a task
    >>> transition_task_status(db_path, 42, 'completed')
    >>>
    >>> # Defer a task (no timestamp needed)
    >>> transition_task_status(db_path, 42, 'deferred')
"""

import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from formaltask.db.connection import DatabaseConnection
from formaltask.db.helpers import ensure_task_exists
from formaltask.utils.constants import TaskStatus

__all__: list[str] = [
    "transition_task_status",
    "InvalidTransitionError",
    "VALID_TRANSITIONS",
]

logger = logging.getLogger(__name__)


class InvalidTransitionError(Exception):
    """Raised when attempting an invalid task status transition."""

    def __init__(
        self, current_status: str, new_status: str, valid_targets: list[str] | None = None
    ):
        self.current_status = current_status
        self.new_status = new_status
        self.valid_targets = valid_targets or []

        if valid_targets:
            targets_str = ", ".join(sorted(valid_targets))
            msg = (
                f"Invalid transition from '{current_status}' to '{new_status}'. "
                f"Valid targets: {targets_str}"
            )
        else:
            msg = (
                f"Invalid transition from '{current_status}' to '{new_status}'. "
                f"See VALID_TRANSITIONS for allowed transitions."
            )
        super().__init__(msg)


# Valid state transitions for task status state machine.
# Maps current_status -> list of allowed next statuses.
VALID_TRANSITIONS: dict[TaskStatus, list[TaskStatus]] = {
    TaskStatus.OPEN: [TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED, TaskStatus.DEFERRED],
    TaskStatus.IN_PROGRESS: [
        TaskStatus.PENDING_MERGE,
        TaskStatus.PENDING_REVIEW,
        TaskStatus.BLOCKED_USER,
        TaskStatus.BLOCKED,
        TaskStatus.COMPLETED,
        TaskStatus.DEFERRED,
        TaskStatus.CANCELLED,
    ],
    TaskStatus.PENDING_MERGE: [TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
    TaskStatus.PENDING_REVIEW: [TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
    TaskStatus.BLOCKED_USER: [TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED, TaskStatus.CANCELLED],
    TaskStatus.BLOCKED: [TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED, TaskStatus.DEFERRED],
    TaskStatus.DEFERRED: [TaskStatus.OPEN, TaskStatus.CANCELLED],
    TaskStatus.COMPLETED: [],  # Terminal state
    TaskStatus.CANCELLED: [],  # Terminal state
}


def transition_task_status(
    db_path: str | Path,
    task_id: int,
    new_status: str,
    *,
    idempotent: bool = False,
    force: bool = False,
    head_commit_sha: str | None = None,
) -> bool:
    """Transition task to new status with proper timestamp coordination.

    This is the SINGLE SOURCE OF TRUTH for all task status changes.

    Args:
        db_path: Path to FormalTask database
        task_id: ID of task to transition
        new_status: Target status (open, in_progress, completed, etc.)
        idempotent: If True, return False instead of error when already in state
                   (used by issue_start for race condition prevention)
        force: If True, skip validation (for data repair only)
        head_commit_sha: SHA of HEAD commit at completion time (optional).
                        Stored only when new_status is 'completed'; ignored
                        for other transitions. Must be a 40-char hex string or None.

    Returns:
        True if transition succeeded, False if no change needed (idempotent mode)

    Raises:
        ValueError: If task_id doesn't exist or status is invalid

    Timestamp Coordination:
        - 'in_progress' -> sets started_at (if not already set)
        - 'completed' -> sets completed_at
        - 'pending_merge', 'blocked', 'deferred', 'cancelled' -> no timestamp changes

    Examples:
        >>> # Start a task (with race protection)
        >>> success = transition_task_status(db_path, 42, 'in_progress', idempotent=True)
        >>> if not success:
        ...     print("Task already started by another process")

        >>> # Complete a task
        >>> transition_task_status(db_path, 42, 'completed')

        >>> # Defer a task (no timestamp needed)
        >>> transition_task_status(db_path, 42, 'deferred')
    """
    db_path = Path(db_path) if isinstance(db_path, str) else db_path

    # Validate status value
    valid_statuses = {status.value for status in TaskStatus}
    if not force and new_status not in valid_statuses:
        raise ValueError(f"Invalid status '{new_status}'. Valid options: {sorted(valid_statuses)}")

    # Validate head_commit_sha format if provided (40 hex chars)
    if head_commit_sha is not None and not re.match(r"^[0-9a-f]{40}$", head_commit_sha):
        raise ValueError(
            f"Invalid head_commit_sha format: '{head_commit_sha}'. "
            "Must be a 40-character hexadecimal string."
        )

    # Use exclusive lock for atomicity
    with DatabaseConnection(db_path, exclusive=True) as conn:
        cursor = conn.cursor()

        # Check if task exists and get current status
        task = ensure_task_exists(cursor, task_id)
        current_status = task["status"]

        # Handle same-status transitions
        if current_status == new_status:
            if idempotent:
                # Idempotent mode: OK to be in desired state already
                logger.debug(
                    f"Task {task_id} already in status '{new_status}', skipping update (idempotent mode)"
                )
                return False
            # Non-idempotent mode: error if trying to transition to same status
            raise ValueError(
                f"Task {task_id} already in status '{new_status}', no transition needed"
            )

        # Validate transition against VALID_TRANSITIONS dict
        if not force:
            try:
                current_enum = TaskStatus(current_status)
            except ValueError:
                # Log unknown status before raising for debugging (Task #1396)
                # NOTE: Uses WARNING level (not DEBUG) because unknown status indicates
                # data integrity issues that require attention - unlike same-status
                # transitions at line 151 which are expected operational behavior.
                logger.warning(
                    f"Task {task_id}: Unknown current status '{current_status}' "
                    f"(attempted transition to '{new_status}')"
                )
                raise InvalidTransitionError(current_status, new_status) from None

            valid_targets = VALID_TRANSITIONS.get(current_enum, [])
            valid_target_values = [target.value for target in valid_targets]

            if new_status not in valid_target_values:
                raise InvalidTransitionError(current_status, new_status, valid_target_values)

        # Generate timestamp for status changes that need it
        now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        # Build update SQL based on which status we're transitioning to
        if new_status == "in_progress":
            # Only set started_at if it's NULL (preserve idempotency)
            cursor.execute(
                "UPDATE tasks SET status = ?, started_at = COALESCE(started_at, ?) WHERE id = ?",
                (new_status, now_iso, task_id),
            )
        elif new_status == "completed":
            # Always set completed_at and head_commit_sha when completing
            cursor.execute(
                "UPDATE tasks SET status = ?, completed_at = ?, head_commit_sha = ? WHERE id = ?",
                (new_status, now_iso, head_commit_sha, task_id),
            )
        else:
            # Other statuses (deferred, pending_merge, blocked, cancelled, open)
            # don't require timestamp coordination
            cursor.execute(
                "UPDATE tasks SET status = ? WHERE id = ?",
                (new_status, task_id),
            )

    logger.debug("Task %s: %s -> %s", task_id, current_status, new_status)
    return True
