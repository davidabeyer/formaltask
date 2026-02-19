#!/usr/bin/env python3
"""Register hooks in Claude Code settings.json."""

import json
import shutil
import sys
from datetime import datetime

from formaltask.paths import get_claude_home, get_hook_script_path


class SettingsNotFoundError(Exception):
    """Raised when settings.json is not found."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Settings file not found: {path}")


class SettingsPermissionError(Exception):
    """Raised when permission denied accessing settings.json."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Permission denied: {path}")


def register_hook(hook_type: str, matcher: str, hook_config: dict) -> bool:
    """Register a hook in settings.json.

    Creates missing hook types and matchers as needed.

    Args:
        hook_type: The hook type (e.g., "Stop", "SessionStart", "PreToolUse")
        matcher: The matcher string (e.g., "", "Bash")
        hook_config: The hook configuration dict with type, command, timeout

    Returns:
        True if hook registered successfully, False otherwise.
    """
    settings_path = get_claude_home() / "settings.json"

    if not settings_path.exists():
        print(f"Settings file not found: {settings_path}", file=sys.stderr)
        return False

    try:
        with open(settings_path) as f:
            settings = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {settings_path}: {e}", file=sys.stderr)
        return False
    except OSError as e:
        print(f"Failed to read {settings_path}: {e}", file=sys.stderr)
        return False

    # Ensure hooks section exists
    if "hooks" not in settings:
        settings["hooks"] = {}

    # Ensure hook type exists
    if hook_type not in settings["hooks"]:
        settings["hooks"][hook_type] = []

    # Find or create matcher entry
    hook_type_list = settings["hooks"][hook_type]
    matcher_entry = next((h for h in hook_type_list if h.get("matcher") == matcher), None)

    if matcher_entry is None:
        matcher_entry = {"matcher": matcher, "hooks": []}
        hook_type_list.append(matcher_entry)

    # Check if hook already registered (by command)
    command = hook_config.get("command")
    if any(h.get("command") == command for h in matcher_entry["hooks"]):
        return True  # Already registered, nothing to do

    # Add the hook
    matcher_entry["hooks"].append(hook_config)

    # Create backup before writing
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    backup_path = settings_path.with_suffix(f".{timestamp}.json.bak")
    try:
        shutil.copy2(settings_path, backup_path)
    except OSError as e:
        print(f"Failed to create backup: {e}", file=sys.stderr)
        return False

    # Write with atomic rename
    temp_path = settings_path.with_suffix(".json.tmp")
    try:
        with open(temp_path, "w") as f:
            json.dump(settings, f, indent=2)
            f.write("\n")
        temp_path.rename(settings_path)
    except OSError as e:
        print(f"Failed to write settings: {e}", file=sys.stderr)
        temp_path.unlink(missing_ok=True)
        return False

    return True


def register_required_hooks() -> list[tuple[str, str]]:
    """Register all required formaltask hooks: Stop, SessionStart, PreToolUse.

    Returns:
        List of tuples (hook_type, status) where status is "registered" or "skipped".

    Raises:
        SettingsNotFoundError: If settings.json doesn't exist.
        SettingsPermissionError: If permission denied reading/writing settings.json.
    """
    settings_path = get_claude_home() / "settings.json"

    # Check settings.json exists
    if not settings_path.exists():
        raise SettingsNotFoundError(str(settings_path))

    # Check we can read it
    try:
        with open(settings_path) as f:
            settings = json.load(f)
    except PermissionError as err:
        raise SettingsPermissionError(str(settings_path)) from err
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {settings_path}: {e}") from e

    hooks_to_register = [
        ("Stop", "", get_hook_script_path("hooks/stop/runner.py"), 5000),
        ("SessionStart", "", get_hook_script_path("hooks/session_start/runner.py"), 10000),
        ("PreToolUse", "", get_hook_script_path("hooks/pretool/runner.py"), 10000),
        ("PostToolUse", "", get_hook_script_path("hooks/posttool/runner.py"), 5000),
        ("UserPromptSubmit", "", get_hook_script_path("hooks/promptsubmit/runner.py"), 5000),
    ]

    results = []
    for hook_type, matcher, command, timeout in hooks_to_register:
        hook_config = {
            "type": "command",
            "command": f"python3 {command}",
            "timeout": timeout,
        }

        # Check if already registered (by command)
        hook_type_list = settings.get("hooks", {}).get(hook_type, [])
        matcher_entry = next((h for h in hook_type_list if h.get("matcher") == matcher), None)
        if matcher_entry and any(
            h.get("command") == hook_config["command"] for h in matcher_entry.get("hooks", [])
        ):
            results.append((hook_type, "skipped"))
        else:
            if not register_hook(hook_type, matcher, hook_config):
                raise SettingsPermissionError(str(settings_path))
            results.append((hook_type, "registered"))

    return results


if __name__ == "__main__":
    sys.exit(
        0
        if register_hook("Stop", "", {"type": "command", "command": "test", "timeout": 2000})
        else 1
    )
