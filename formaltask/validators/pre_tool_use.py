#!/usr/bin/env python3
"""
PreToolUse Hook: Path Validation

Blocks deprecated path patterns and suggests correct locations.
Follows Claude Code hook conventions with exit code pattern.
"""

import re

# Tools that this validator applies to
TOOL_MATCH = ["Write", "Edit", "MultiEdit"]


def check(ctx: dict) -> dict | None:
    """Validate file paths against information architecture rules.

    Args:
        ctx: Hook context dict with tool_name and tool_input.

    Returns:
        None if allowed (valid path or non-matching tool),
        dict with decision='block' and reason if deprecated path detected.
    """
    tool_name = ctx.get("tool_name", "")

    # Only validate Write, Edit, MultiEdit tools
    if tool_name not in TOOL_MATCH:
        return None

    tool_input = ctx.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        return None

    # Check for deprecated .claude/prds/ pattern
    if ".claude/prds/" in file_path:
        match = re.search(r"\.claude/prds/([^/]+)\.md", file_path)
        feature_name = match.group(1) if match else "feature-name"
        reason = (
            f"BLOCKED: Deprecated path pattern detected\n\n"
            f"File: {file_path}\n"
            f"Issue: PRDs should be stored in epic directories\n\n"
            f"Correct location: plans/epics/{feature_name}/prd.md"
        )
        return {"decision": "block", "reason": reason}

    # Check for deprecated .claude/epics/ pattern
    if ".claude/epics/" in file_path:
        match = re.search(r"\.claude/epics/([^/]+)/", file_path)
        epic_name = match.group(1) if match else "epic-name"
        reason = (
            f"BLOCKED: Deprecated path pattern detected\n\n"
            f"File: {file_path}\n"
            f"Issue: Epic files should be stored in plans/epics directory\n\n"
            f"Correct location: plans/epics/{epic_name}/epic.md"
        )
        return {"decision": "block", "reason": reason}

    # Check for deprecated Memory/sessions/ pattern
    if "Memory/sessions/" in file_path:
        match = re.search(r"Memory/sessions/([^/]+)/", file_path)
        topic = match.group(1) if match else "topic"
        reason = (
            f"BLOCKED: Deprecated path pattern detected\n\n"
            f"File: {file_path}\n"
            f"Issue: Session files should be stored in sessions directory (not Memory/)\n\n"
            f"Correct location: sessions/{topic}/"
        )
        return {"decision": "block", "reason": reason}

    # Check for deprecated Memory/MOCs/ pattern
    if "Memory/MOCs/" in file_path:
        match = re.search(r"Memory/MOCs/([^/]+)\.md", file_path)
        topic = match.group(1) if match else "topic"
        reason = (
            f"BLOCKED: Deprecated path pattern detected\n\n"
            f"File: {file_path}\n"
            f"Issue: MOC files should be stored in index/topics directory (not Memory/)\n\n"
            f"Correct location: index/topics/{topic}.md"
        )
        return {"decision": "block", "reason": reason}

    return None
