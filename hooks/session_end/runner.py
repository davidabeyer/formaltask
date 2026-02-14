#!/usr/bin/env python3
"""SessionEnd hook runner - plain function architecture.

Task #2583: Simple list + loop pattern (no discovery).
Reads stdin JSON payload and executes all phases in order.
"""

import json
import sys
from pathlib import Path

# Add project root for imports when run directly
_project_root = str(Path(__file__).parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from hooks.session_end.phases import PHASES


def main() -> None:
    """Entry point for SessionEnd hook.

    Executes all phases in order. All phases fail open
    (errors logged but don't block session end).
    """
    payload = json.load(sys.stdin)

    # Skip if no session_id (nothing to analyze)
    if not payload.get("session_id"):
        print(json.dumps({}))
        return

    for phase_fn in PHASES:
        try:
            phase_fn(payload)
        except Exception as e:
            # Fail open: log error but continue with remaining phases
            print(f"Warning: {phase_fn.__name__} failed: {e}", file=sys.stderr)

    # SessionEnd never blocks, just outputs empty
    print(json.dumps({}))


if __name__ == "__main__":
    main()
