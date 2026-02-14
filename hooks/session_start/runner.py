#!/usr/bin/env python3
"""SessionStart hook runner - plain function architecture.

Task #2582: Simple list + loop pattern (no discovery).
Task #2623: Output task context to stdout for worker injection.
Reads stdin JSON payload and executes all phases in order.
"""

import json
import sys
from pathlib import Path

# Add project root for imports when run directly
_project_root = str(Path(__file__).parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from hooks.session_start.phases import PHASES


def main() -> None:
    """Entry point for SessionStart hook.

    Executes all phases in order. All phases fail open
    (errors logged but don't block session start).

    Task context is output to stdout for Claude Code to inject
    as additionalContext into the worker session.
    """
    payload = json.load(sys.stdin)
    hook_output = None

    for phase_fn in PHASES:
        try:
            result = phase_fn(payload)
            # Collect hookSpecificOutput from phases that return it
            if result and isinstance(result, dict) and "hookSpecificOutput" in result:
                hook_output = result
        except Exception as e:
            # Fail open: log error but continue with remaining phases
            print(f"Warning: {phase_fn.__name__} failed: {e}", file=sys.stderr)

    # Output collected hook response to stdout (Task #2623)
    # Claude Code expects JSON with hookSpecificOutput.additionalContext
    if hook_output:
        print(json.dumps(hook_output))


if __name__ == "__main__":
    main()
