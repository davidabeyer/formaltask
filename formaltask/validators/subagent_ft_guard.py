#!/usr/bin/env python3
"""PreToolUse Hook: Restrict ft commands for subagents.

Subagents can only run `ft review store`. All other ft commands are blocked.
This prevents subagents from calling `ft work blocked` or other privileged commands.

Used in subagent frontmatter hooks, not global settings.json.
"""

import json
import re
import sys

# Commands subagents ARE allowed to run (noun + verb)
ALLOWED_FT_COMMANDS = frozenset({"review store"})

BLOCKED_MESSAGE = (
    "BLOCKED: Subagents can only run 'ft review store'.\n"
    "Other ft commands must be run by the orchestrator."
)


def check(ctx: dict) -> dict | None:
    """Validate subagent ft command access.

    Args:
        ctx: Hook context dict with tool_name and tool_input.

    Returns:
        None if allowed, dict with decision='block' if restricted command.
    """
    tool_name = ctx.get("tool_name", "")

    if tool_name != "Bash":
        return None

    command = ctx.get("tool_input", {}).get("command", "")
    if not command:
        return None

    # Check for ft commands (ft or python3 -m formaltask.cli.pm)
    # Capture noun and optional verb: "ft review store" → "review store"
    ft_match = re.search(
        r"\b(?:ft|python3?\s+-m\s+formaltask\.cli\.pm)\s+(\S+)(?:\s+(\S+))?", command
    )
    if not ft_match:
        return None

    noun = ft_match.group(1)
    verb = ft_match.group(2) or ""
    ft_command = f"{noun} {verb}".strip()

    if ft_command in ALLOWED_FT_COMMANDS:
        return None

    return {"decision": "block", "reason": BLOCKED_MESSAGE}


def main() -> None:
    """Hook entry point."""
    try:
        ctx = json.load(sys.stdin)
        result = check(ctx)
        if result:
            print(json.dumps(result))
            sys.exit(2)
    except json.JSONDecodeError:
        pass  # Fail open for malformed input


if __name__ == "__main__":
    main()
