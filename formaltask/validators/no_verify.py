#!/usr/bin/env python3
"""PreToolUse hook to block git commit --no-verify."""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import json
import re
import sys


def check(ctx: dict) -> dict | None:
    """Block git commit --no-verify or -n flag.

    Args:
        ctx: Hook context dict with tool_name and tool_input.

    Returns:
        None if allowed, or dict with decision='block' and reason if blocked.
    """
    if ctx.get("tool_name") != "Bash":
        return None

    command = ctx.get("tool_input", {}).get("command", "")

    if not re.search(r"git\s+commit\b", command):
        return None

    # Case-insensitive check for --no-verify (P1 fix)
    if "--no-verify" in command.lower():
        return {
            "decision": "block",
            "reason": "🚫 --no-verify blocked. Doc-guard pre-commit checks are required.",
        }

    # Match -n in combined flags like -nm, -an, -anm (P0 security fix)
    if re.search(r"git\s+commit\b.*\s-[a-z]*n", command):
        return {
            "decision": "block",
            "reason": "🚫 -n flag blocked. Doc-guard pre-commit checks are required.",
        }

    return None


def main():
    """Main entry point for PreToolUse hook."""
    try:
        data = json.load(sys.stdin)
        result = check(data)
        if result is not None:
            # Convert to Claude Code hook output format
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": result["reason"],
                }
            }
            print(json.dumps(output))
        return 0
    except Exception as e:
        sys.stderr.write(f"no_verify_blocker error: {e}\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
