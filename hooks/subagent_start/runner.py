#!/usr/bin/env python3
"""SubagentStart hook - inject review-store instructions proactively.

Task #2658: Reduce token wastage by telling workers about review storage upfront.
"""

import json
import sys
from pathlib import Path

# Add project root for imports when run directly
_project_root = str(Path(__file__).parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _get_task_id_from_cwd(cwd: str | None) -> int | None:
    """Extract task ID from worktree .task/id file."""
    if not cwd:
        return None
    task_id_file = Path(cwd) / ".task" / "id"
    if not task_id_file.exists():
        return None
    try:
        return int(task_id_file.read_text().strip())
    except (ValueError, OSError):
        return None


REVIEW_STORE_INSTRUCTIONS = """## Review Storage (IMPORTANT)

When you complete a review, output an `@@@REVIEW` packet and store it:

```
@@@REVIEW
{"task_id": <id>, "review_type": "<type>", "severity": "clean|minor|major|critical", "findings": [...], "summary": "..."}
@@@
```

Then run: `python3 -m formaltask.cli.pm review-store '<JSON>'`

This must happen BEFORE task completion."""


def main() -> dict:
    """Inject review-store instructions for task worktrees."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return {}

    cwd = input_data.get("cwd")
    task_id = _get_task_id_from_cwd(cwd)

    # Not a task worktree - no injection needed
    if task_id is None:
        return {}

    # Inject review-store instructions
    return {"hookSpecificOutput": {"additionalContext": REVIEW_STORE_INSTRUCTIONS}}


if __name__ == "__main__":
    print(json.dumps(main()))
