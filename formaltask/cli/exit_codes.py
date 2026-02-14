"""POSIX-compliant exit codes for agent-optimal CLI.

Exit codes follow POSIX conventions with 64+ reserved for application-specific codes:
- 0: Success
- 1-2: Standard error codes
- 64-71: Resource errors (not found, already exists, invalid state, conflict)

Usage Guide
-----------
SUCCESS (0): Command completed successfully
GENERAL_ERROR (1): Unspecified error (catch-all)
USAGE_ERROR (2): Invalid command syntax or arguments
NOT_FOUND (64): Requested resource doesn't exist (epic, task)
ALREADY_EXISTS (65): Resource already exists (duplicate creation)
INVALID_STATE (66): State machine error (e.g., invalid status transition)
CONFLICT (67): Dependency conflicts, concurrent modifications
VALIDATION_ERROR (68): Input validation failed (e.g., content too long)

Agent Integration
-----------------
Agents should check exit codes for automation decisions:
- 0: Proceed to next step
- 2, 64-68: User/input error, report and stop
- 1: System error, consider retry or escalate

Example::

    import subprocess
    from formaltask.cli.exit_codes import ExitCode

    result = subprocess.run(["python3", "-m", "formaltask.cli.pm", "task-complete", "42"])
    if result.returncode == ExitCode.NOT_FOUND:
        print("Task 42 doesn't exist")
    elif result.returncode == ExitCode.INVALID_STATE:
        print("Task cannot be completed from current state")
"""

from enum import IntEnum

__all__ = ["ExitCode"]


class ExitCode(IntEnum):
    """Exit codes for CLI commands."""

    SUCCESS = 0
    GENERAL_ERROR = 1
    USAGE_ERROR = 2

    # Resource errors (64-71)
    NOT_FOUND = 64
    ALREADY_EXISTS = 65
    INVALID_STATE = 66  # State machine error (e.g., invalid status transition)
    CONFLICT = 67  # Dependency conflicts, concurrent modifications
    VALIDATION_ERROR = 68  # Input validation failed (e.g., content too long)
    CONFIG_ERROR = 69  # Configuration file missing or invalid
