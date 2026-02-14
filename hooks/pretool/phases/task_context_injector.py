"""PreToolUse phase: Remind Claude to provide context when spawning subagents.

Injects a reminder for ALL Task calls to include TARGET, CONTEXT, and TASK.
During skill runs, also reminds about OUTPUT paths.
"""

import json
import logging
from pathlib import Path

from formaltask.utils import get_current_session_id

logger = logging.getLogger(__name__)

ACTIVE_SKILLS_BREADCRUMB = Path.home() / ".claude" / "tmp" / "active-skills.json"


def _get_active_skill_run() -> dict | None:
    """Get the most recent active skill run for this session."""
    if not ACTIVE_SKILLS_BREADCRUMB.exists():
        return None

    session_id = get_current_session_id()
    if not session_id:
        return None

    try:
        skills = json.loads(ACTIVE_SKILLS_BREADCRUMB.read_text())
        if not isinstance(skills, list):
            return None

        # Find most recent skill for this session
        for skill in reversed(skills):
            if skill.get("session_id") == session_id:
                return skill
    except (json.JSONDecodeError, OSError):
        pass

    return None


def check(ctx: dict) -> dict | None:
    """Inject context guidance into ALL Task prompts."""
    if ctx.get("tool_name") != "Task":
        return None

    active = _get_active_skill_run()
    skill = active.get("skill", "unknown") if active else None

    if skill:
        # During skill runs: include OUTPUT path reminder
        context = f"""## Subagent Context (`{skill}`)

Subagents start with zero context. Your prompt is their entire world.

**Include:**
- WHAT: Exact files/functions to examine
- CONTEXT: What you found that they need to know
- TASK: Specific deliverable
- OUTPUT: Where to write (use injected paths)
"""
    else:
        # Direct invoke: agents return to conversation, no OUTPUT needed
        context = """## Subagent Context

Subagents start with zero context. Your prompt is their entire world.

**Include:**
- WHAT: Exact files/functions to examine
- CONTEXT: What you found that they need to know
- TASK: Specific deliverable
"""

    return {"additionalContext": context}
