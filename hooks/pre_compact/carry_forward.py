"""PreCompact hook: carry forward breadcrumbs across compaction.

Writes the dying session's ID to a carry-forward file so the next
SessionStart can re-tag orphaned skill breadcrumbs with the new session_id.

Without this, compaction breaks contract enforcement because breadcrumbs
are keyed by session_id, which changes on compaction.
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

CARRY_FORWARD_FILE = Path.home() / ".claude" / "tmp" / "compacting-session.json"


def carry_forward_breadcrumbs(ctx: dict, *, carry_file: Path = CARRY_FORWARD_FILE) -> None:
    session_id = ctx.get("session_id")
    if not session_id:
        return

    carry_file.parent.mkdir(parents=True, exist_ok=True)
    carry_file.write_text(
        json.dumps(
            {
                "old_session_id": session_id,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
    )


def main() -> None:
    payload = json.load(sys.stdin)
    carry_forward_breadcrumbs(payload)


if __name__ == "__main__":
    main()
