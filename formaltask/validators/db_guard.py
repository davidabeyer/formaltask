#!/usr/bin/env python3
"""PreToolUse Hook: FormalTask Database Guard"""

import os
import shlex

# Canonical database path - uses PROJECT_ROOT env var or cwd
_project_root = os.getenv("PROJECT_ROOT", os.getcwd())
CANONICAL_DB_PATH = os.path.join(_project_root, ".claude", "formaltask.db")


def is_formaltask_command(command: str) -> bool:
    """Detect if command is a FormalTask CLI command."""
    return "formaltask.cli.pm" in command


def extract_db_path(command: str) -> str | None:
    """Extract --db-path value from command.

    Uses shlex.split() for proper shell argument parsing to handle
    quoted paths correctly (e.g., --db-path "/path with spaces/db").
    """
    try:
        args = shlex.split(command)
        for i, arg in enumerate(args):
            if arg == "--db-path" and i + 1 < len(args):
                return args[i + 1]
            if arg.startswith("--db-path="):
                return arg.split("=", 1)[1]
        return None
    except ValueError:
        # shlex.split can raise ValueError on unclosed quotes
        return None


def is_canonical_path(path: str) -> bool:
    """Check if path resolves to canonical database path.

    Security note: Uses abspath() (not realpath()) intentionally.
    This BLOCKS symlinks even if they point to canonical, which is
    the secure behavior - we want explicit canonical paths only.
    """
    return os.path.abspath(path) == CANONICAL_DB_PATH


def validate_formaltask_db(tool_input: dict) -> dict:
    """Validate FormalTask database path in tool input.

    Returns:
        Empty dict to allow, dict with 'error' key to block.
    """
    try:
        command = tool_input.get("command", "")
        if not command or not is_formaltask_command(command):
            return {}  # Not our concern - allow

        db_path = extract_db_path(command)
        if db_path is None:
            return {}  # No explicit path - uses default, allow

        if is_canonical_path(db_path):
            return {}  # Canonical path - allow

        return {"error": f"FormalTask operations must use canonical database: {CANONICAL_DB_PATH}"}
    except Exception as e:
        # SECURITY: Fail-closed - deny on any validation error
        return {"error": f"Validation error: {e}"}


def check(ctx: dict) -> dict | None:
    """Validate FormalTask database path in tool input.

    Security-critical validator with FAIL_CLOSED behavior.

    Args:
        ctx: Hook context dict with tool_name and tool_input.

    Returns:
        None if allowed, or dict with decision='block' and reason if blocked.
    """
    # Non-Bash tools are not our concern
    if ctx.get("tool_name") != "Bash":
        return None

    tool_input = ctx.get("tool_input", {})
    result = validate_formaltask_db(tool_input)

    if "error" in result:
        return {"decision": "block", "reason": result["error"]}
    return None


def main() -> None:
    """Hook entry point for standalone execution."""
    import json
    import sys

    try:
        ctx = json.load(sys.stdin)
        result = check(ctx)
        if result:
            print(json.dumps(result))
    except json.JSONDecodeError:
        # Fail-closed for security: block on malformed input
        print(json.dumps({"decision": "block", "reason": "Malformed JSON input"}))


if __name__ == "__main__":
    main()
