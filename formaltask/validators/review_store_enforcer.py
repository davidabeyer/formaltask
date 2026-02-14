#!/usr/bin/env python3
"""Stop Hook: Enforce review storage before code-reviewer exits.

Task #2834: Parses transcript for 'review store' command execution.
Blocks stop if review wasn't stored.

Used in code-reviewer agent frontmatter Stop hook.
"""

import json
import sys


def check(ctx: dict) -> dict | None:
    """Block stop if review store wasn't called.

    Args:
        ctx: Hook context with transcript_path.

    Returns:
        None if review was stored, dict with decision='block' otherwise.
    """
    transcript_path = ctx.get("transcript_path")
    if not transcript_path:
        return None  # Fail open if no transcript

    try:
        with open(transcript_path) as f:
            content = f.read()
            if "review store" in content:
                return None  # Review was stored
    except OSError:
        return None  # Fail open on file errors

    return {
        "decision": "block",
        "reason": (
            "Store review before exiting:\npython3 -m formaltask.cli.pm review store '<JSON>'"
        ),
    }


def main() -> None:
    """Hook entry point."""
    try:
        ctx = json.load(sys.stdin)
        result = check(ctx)
        if result:
            print(json.dumps(result))
    except json.JSONDecodeError:
        pass  # Fail open for malformed input


if __name__ == "__main__":
    main()
