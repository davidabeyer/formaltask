"""UserPromptSubmit phase functions.

Plain function architecture (no phase_engine).
Simple list + loop pattern for promptsubmit hook.
"""

from hooks.promptsubmit.phases import (
    task_context,
    update_session_activity,
)

PHASES = [
    update_session_activity.check,
    task_context.check,
]

__all__ = [
    "task_context",
    "update_session_activity",
    "PHASES",
]
