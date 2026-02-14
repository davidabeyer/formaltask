"""UserPromptSubmit phase functions.

Task #2569: Plain function architecture (no phase_engine).
Simple list + loop pattern for promptsubmit hook.
"""

from hooks.promptsubmit.phases import (
    prompt_optimizer,
    skill_queue_reminder,
    skill_run_initializer,
    task_context,
    update_session_activity,
)

# Ordered list of phase check functions (for runner to iterate)
# skill_run_initializer first so SkillRun is created before skill loads
# skill_queue_reminder last — fires every turn during active skill sessions
PHASES = [
    update_session_activity.check,
    skill_run_initializer.check,
    prompt_optimizer.check,
    task_context.check,
    skill_queue_reminder.check,
]

__all__ = [
    "prompt_optimizer",
    "skill_queue_reminder",
    "skill_run_initializer",
    "task_context",
    "update_session_activity",
    "PHASES",
]
