#!/usr/bin/env python3
"""PostToolUse hook runner - plain function architecture.

Task #2583: Simple list + loop pattern (no discovery).
Reads stdin JSON payload and executes all phases in order.
Outputs JSON with additionalContext if any phase returns it.
"""

import json
import sys
from pathlib import Path

# Add project root for imports when run directly
_project_root = str(Path(__file__).parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from hooks.posttool.phases import PHASES


def main() -> None:
    """Entry point for PostToolUse hook.

    Executes all phases in order. All phases fail open
    (errors logged but don't block tool completion).
    If any phase returns a dict with additionalContext, outputs it.
    """
    payload = json.load(sys.stdin)
    result = {}

    for phase_fn in PHASES:
        try:
            ret = phase_fn(payload)
            if isinstance(ret, dict) and "additionalContext" in ret:
                result["additionalContext"] = ret["additionalContext"]
        except Exception as e:
            # Fail open: log error but continue with remaining phases
            print(f"Warning: {phase_fn.__name__} failed: {e}", file=sys.stderr)

    if result:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
