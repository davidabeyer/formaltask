"""Bash file modification guard - prevents TDD guard bypass via shell commands."""

import re

# Patterns compiled once at module level
_FILE_MODIFY_PATTERNS = [
    re.compile(r"\bsed\b[^|;&\n]*\s-i\b", re.IGNORECASE),  # sed with -i flag
    re.compile(r"\bsed\s+--in-place\b", re.IGNORECASE),  # sed --in-place
    re.compile(r"\becho\s+.*>\s*\S+\.py", re.IGNORECASE),  # echo ... > file.py
]


def check(ctx: dict) -> dict | None:
    """Block file-modifying bash commands.

    Args:
        ctx: Hook context dict with tool_name and tool_input.

    Returns:
        None if allowed, or dict with decision='block' and reason if blocked.
    """
    if ctx.get("tool_name") != "Bash":
        return None

    command = ctx.get("tool_input", {}).get("command", "")

    for pattern in _FILE_MODIFY_PATTERNS:
        if pattern.search(command):
            return {
                "decision": "block",
                "reason": (
                    f"Bash file modification blocked. Use Edit/Write tools instead. "
                    f"Matched pattern: {pattern.pattern}"
                ),
            }

    return None
