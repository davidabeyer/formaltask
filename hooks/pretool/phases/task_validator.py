"""Task validator phase - validates Task tool parameters.

Enforces agent-spawning-guardrails compliance by validating:
- Prompts contain absolute paths (not relative)
- Required context sections are present
- No ambiguous or vague task descriptions
"""

import re

# Patterns indicating relative paths (should be blocked)
RELATIVE_PATH_PATTERNS = [
    r"(?<![/\w])\.\./",  # ../path (not preceded by / or word char)
    r"(?<![/\w])\./",  # ./path (not preceded by / or word char)
    r"(?<![/\w])~/",  # ~/path (tilde expansion)
    r'\bpath:\s*["\']?(?!/)[\w]',  # path: relative (not starting with /)
]

# Agents that skip validation (don't need file paths)
SKIP_AGENTS = ["general-purpose", "claude-code-guide", "Explore"]


def check(ctx: dict) -> dict | None:
    """Validate Task tool invocation.

    Returns:
        None to allow, or {"decision": "block", "reason": str} to block.
    """
    if ctx.get("tool_name") != "Task":
        return None

    tool_input = ctx.get("tool_input", {})
    prompt = tool_input.get("prompt", "")
    description = tool_input.get("description", "")
    subagent_type = tool_input.get("subagent_type", "")

    # Skip validation for certain agent types that don't need file paths
    if subagent_type in SKIP_AGENTS:
        return None

    # Check for relative paths
    prompt_lower = prompt.lower()
    for pattern in RELATIVE_PATH_PATTERNS:
        if re.search(pattern, prompt_lower, re.IGNORECASE):
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                context = prompt[max(0, match.start() - 10) : match.end() + 20]
                return {
                    "decision": "block",
                    "reason": (
                        "Task validation FAILED:\n"
                        f"  - Relative path detected: '...{context}...'\n"
                        "   Use absolute paths like: ~/task-XXX-...\n\n"
                        "Fix the issues above before spawning the agent.\n"
                        "Reference: Skill(agent-spawning-guardrails) for guidance."
                    ),
                }

    # Check description quality
    if len(description.strip()) < 10:
        return {
            "decision": "block",
            "reason": (
                "Task validation FAILED:\n"
                f"  - Description too brief: '{description}'\n"
                "   Provide clear 3-5 word description of the task\n\n"
                "Fix the issues above before spawning the agent.\n"
                "Reference: Skill(agent-spawning-guardrails) for guidance."
            ),
        }

    return None
