"""PreToolUse phase: Enforce prompt structure for Task subagents.

Custom agents need TARGET. OUTPUT PATH only required during skill runs
(when agents write to {outputs}/ paths).
"""

import json
import logging
import os
import re
from pathlib import Path

from formaltask.utils import get_current_session_id, get_current_transcript_path

logger = logging.getLogger(__name__)

BUILTIN_AGENT_TYPES = frozenset({"general-purpose", "Explore", "Plan"})

# During skill runs: agents write to files, need output path
SKILL_REQUIRED = ["TARGET", "OUTPUT PATH"]
# Direct invoke: agents return to conversation, just need target
DIRECT_REQUIRED = ["TARGET"]

CUSTOM_AGENT_DIRS = [
    Path.home() / ".claude" / "agents",
    Path(os.getenv("PROJECT_ROOT", ".")) / ".claude" / "agents",
]

GUIDELINES_PATH = Path(__file__).parent.parent / "prompt_guidelines.md"
ACTIVE_SKILLS_BREADCRUMB = Path.home() / ".claude" / "tmp" / "active-skills.json"
CURRENT_SESSION_FILE = Path.home() / ".claude" / "tmp" / "current-session.json"

_guidelines_cache: str | None = None


def _is_skill_active() -> bool:
    """Check if a skill run is active for this conversation.

    Uses transcript_path as primary key (stable across hook types),
    falls back to session_id for breadcrumbs written before this fix.
    """
    if not ACTIVE_SKILLS_BREADCRUMB.exists():
        return False

    transcript_path = get_current_transcript_path()
    session_id = get_current_session_id()
    if not transcript_path and not session_id:
        return False

    try:
        skills = json.loads(ACTIVE_SKILLS_BREADCRUMB.read_text())
        if not isinstance(skills, list):
            return False

        for skill in reversed(skills):
            if transcript_path and skill.get("transcript_path") == transcript_path:
                return True
            if session_id and skill.get("session_id") == session_id:
                return True
    except (json.JSONDecodeError, OSError):
        pass

    return False


def _load_guidelines() -> str:
    global _guidelines_cache
    if _guidelines_cache is None:
        try:
            _guidelines_cache = GUIDELINES_PATH.read_text()
        except OSError as e:
            logger.warning("Failed to load prompt guidelines: %s", e)
            _guidelines_cache = ""
    return _guidelines_cache


def _is_custom_agent(subagent_type: str) -> bool:
    """Check if agent file exists in custom agent directories."""
    if not subagent_type:
        return False
    for agent_dir in CUSTOM_AGENT_DIRS:
        if not agent_dir.exists():
            continue
        if (agent_dir / f"{subagent_type}.md").exists():
            return True
        for subdir in agent_dir.iterdir():
            if subdir.is_dir() and (subdir / f"{subagent_type}.md").exists():
                return True
    return False


def _check_required_context(prompt: str, required: list[str]) -> list[str]:
    """Return list of missing required context sections."""
    missing = []
    for field in required:
        # Accept: ## FIELD, **FIELD**:, **FIELD:**, FIELD: (at line start)
        patterns = [
            rf"##\s*{re.escape(field)}\b",
            rf"\*\*{re.escape(field)}\*\*:",
            rf"\*\*{re.escape(field)}:\*\*",
            rf"^{re.escape(field)}:",
        ]
        found = any(re.search(p, prompt, re.IGNORECASE | re.MULTILINE) for p in patterns)
        if not found:
            missing.append(field)
    return missing


def _prompt_is_optimized(prompt: str) -> bool:
    """Check if prompt shows intentional structure."""
    p = prompt.strip()
    return p.startswith(("ROLE:", "<role>", "**ROLE**", "**Role:**"))


def check(ctx: dict) -> dict | None:
    """Inject prompt guidance for Task calls.

    Custom agents:
      - Skill runs: remind about TARGET + OUTPUT PATH
      - Direct invoke: remind about TARGET
    Built-in agents: remind about ROLE: prefix.
    """
    if ctx.get("tool_name") != "Task":
        return None

    tool_input = ctx.get("tool_input", {})
    subagent_type = tool_input.get("subagent_type", "")
    prompt = tool_input.get("prompt", "")

    # Custom agents: skill vs direct invoke have different requirements
    if subagent_type and subagent_type not in BUILTIN_AGENT_TYPES:
        if _is_custom_agent(subagent_type):
            skill_active = _is_skill_active()
            required = SKILL_REQUIRED if skill_active else DIRECT_REQUIRED
            missing = _check_required_context(prompt, required)

            if missing:
                if skill_active:
                    return {
                        "additionalContext": f"""Subagent prompt guidance: This agent is BLIND to this conversation.

If it's not in the prompt, it doesn't exist.

Missing sections: {", ".join(missing)}

Include:
## TARGET
[What to analyze - specific files, modules, or features]

## OUTPUT PATH
[Where to write findings - use {{outputs}}/filename.md]

The Copy-Paste Test: Could a stranger complete this task with ONLY your prompt?"""
                    }
                return {
                    "additionalContext": f"""Subagent prompt guidance: This agent is BLIND to this conversation.

If it's not in the prompt, it doesn't exist.

Missing: {", ".join(missing)}

Include:
## TARGET
[What to analyze - specific files, modules, or features]

Be specific. "Review the auth code" fails. "Review src/auth/login.py:50-120 for session handling" works."""
                }
            return None

    # Built-in agents: remind about ROLE: prefix
    if _prompt_is_optimized(prompt):
        return None

    guidelines = _load_guidelines()

    return {
        "additionalContext": f"""Subagent prompt guidance: Effective subagent prompts start with ROLE: to set context.

Review these guidelines for better results:

{guidelines}"""
    }
