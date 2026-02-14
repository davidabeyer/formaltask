"""Centralized constants for FormalTask system.

This module provides StrEnum types for status values, ensuring type safety
while maintaining backward compatibility with existing string comparisons.

Example:
    >>> from formaltask.utils.constants import TaskStatus
    >>> TaskStatus.OPEN == "open"
    True
    >>> status = TaskStatus.IN_PROGRESS
    >>> f"Status is {status}"
    'Status is in_progress'
"""

from enum import StrEnum


class TaskStatus(StrEnum):
    """Task lifecycle status values.

    Uses StrEnum for backward compatibility - values compare equal to strings.

    Status transitions:
        OPEN -> IN_PROGRESS -> PENDING_MERGE -> COMPLETED
                           -> PENDING_REVIEW -> COMPLETED
                           -> BLOCKED_USER -> IN_PROGRESS
                           -> BLOCKED
                           -> DEFERRED
                           -> CANCELLED

    IPC States:
        PENDING_REVIEW: Worker completed, awaiting user review
        BLOCKED_USER: Worker blocked, needs user input
    """

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_MERGE = "pending_merge"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    DEFERRED = "deferred"
    CANCELLED = "cancelled"
    PENDING_REVIEW = "pending_review"
    BLOCKED_USER = "blocked_user"


class WorkerPhase(StrEnum):
    """Worker phase values derived from task state.

    Uses StrEnum for backward compatibility - values compare equal to strings.

    These phases are returned by derive_worker_phase() in state_manager.py
    and used by stop_completion_enforcer.py to gate worker stop events.

    Phase priority (from derive_worker_phase):
        1. BLOCKED - Worker blocked, needs user input
        2. NEEDS_REFLECTION - No learnings captured, run /reflect
        3. NEEDS_HUMAN - P0/P1 finding escalated with needshuman disposition
        4. NEEDS_FIX - P2/P3 findings not yet resolved
        5. IMPLEMENTING - No reviews yet, still coding
        6. NEEDS_PR - Reviews passed, needs to create PR
        7. AWAITING_MERGE - PR exists, waiting for merge
        8. DONE - Task completed (cancelled or PR merged)
    """

    IMPLEMENTING = "implementing"
    NEEDS_REFLECTION = "needs_reflection"
    NEEDS_HUMAN = "needs_human"
    NEEDS_FIX = "needs_fix"
    NEEDS_PR = "needs_pr"
    AWAITING_MERGE = "awaiting_merge"
    DONE = "done"
    BLOCKED = "blocked"


class FindingPriority(StrEnum):
    """Critique finding priority levels."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class ReviewSeverity(StrEnum):
    """Task review severity levels."""

    CLEAN = "clean"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class DispositionType(StrEnum):
    """Finding disposition types."""

    WONTFIX = "wontfix"
    NEEDSHUMAN = "needshuman"
    FIXED = "fixed"
