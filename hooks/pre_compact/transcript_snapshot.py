"""PreCompact hook: snapshot transcript for post-compaction delta generation.

Saves raw transcript before compaction destroys it. No LLM call — pure I/O.
Activation: .session/name file in cwd (worktree-only).
Writes: .session/transcript_snapshot.json
Timeout: 5s (pure I/O, no LLM)
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root for imports when run directly
_project_root = str(Path(__file__).parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from hooks.pre_compact.handoff_transcript import handoff_transcript

COMPACTION_PREAMBLE = "This session is being continued from a previous conversation"


def find_last_compaction_line(transcript_path: Path) -> int:
    """Find the line number after the last compaction summary.

    Returns the line number to start extracting from (0 if no compaction found).
    """
    last_compaction_line = 0

    with open(transcript_path) as f:
        for line_num, line in enumerate(f):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "user":
                continue
            content = entry.get("message", {}).get("content", "")
            if isinstance(content, str) and COMPACTION_PREAMBLE in content:
                # Start AFTER this compaction message
                last_compaction_line = line_num + 1

    return last_compaction_line


def snapshot_transcript(ctx: dict) -> Path | None:
    """Save conversation transcript before compaction destroys it.

    Only captures content since the last compaction (or session start).

    Args:
        ctx: PreCompact hook context with transcript_path and cwd.

    Returns:
        Path to snapshot file, or None if not activated.
    """
    transcript_path_str = ctx.get("transcript_path")
    if not transcript_path_str:
        return None

    transcript_path = Path(transcript_path_str)
    if not transcript_path.exists():
        return None

    cwd = Path(ctx.get("cwd", os.getcwd()))
    session_name_file = cwd / ".session" / "name"

    if not session_name_file.exists():
        return None

    thread_name = session_name_file.read_text().strip()

    # Only extract from last compaction point forward
    start_line = find_last_compaction_line(transcript_path)
    transcript = handoff_transcript(transcript_path, start_line=start_line)

    snapshot = {
        "thread_name": thread_name,
        "transcript": transcript,
        "transcript_path": str(transcript_path),
        "timestamp": datetime.now(UTC).isoformat(),
    }

    snapshot_path = cwd / ".session" / "transcript_snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot))
    return snapshot_path


def main() -> None:
    """Entry point for PreCompact hook."""
    payload = json.load(sys.stdin)
    snapshot_transcript(payload)


if __name__ == "__main__":
    main()
