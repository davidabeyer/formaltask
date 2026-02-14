#!/usr/bin/env python3
"""PreToolUse Hook: Restrict subagent writes to markdown files only.

Simple guard to prevent subagents from accidentally writing to code files,
config files, or system files. Subagents should only output markdown reports.
"""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import json
import sys

# Tools that write files
TOOL_MATCH = ["Write", "Edit", "mcp__morph-mcp__edit_file"]


def check(ctx: dict) -> dict | None:
    """Validate Write/Edit tool calls target markdown files only.

    Args:
        ctx: Hook context dict with tool_name and tool_input.

    Returns:
        None if allowed (.md file),
        dict with decision='block' if not a markdown file.
    """
    tool_name = ctx.get("tool_name", "")

    # Only validate file-writing tools
    if tool_name not in TOOL_MATCH:
        return None

    tool_input = ctx.get("tool_input", {})

    # Get file path (different field names for different tools)
    file_path = tool_input.get("file_path") or tool_input.get("path", "")
    if not file_path:
        return None  # No path to validate

    # Simple check: must end in .md or .json (for structured audit output)
    if file_path.endswith((".md", ".json")):
        return None

    return {
        "decision": "block",
        "reason": (
            f"BLOCKED: Subagents can only write markdown or JSON files.\n"
            f"  Target: {file_path}\n"
            f"  Required: File must end in .md or .json"
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
        # Fail open for malformed input
        pass


if __name__ == "__main__":
    main()
