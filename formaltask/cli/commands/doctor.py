"""ft doctor - Check formaltask basics."""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from formaltask.cli.exit_codes import ExitCode
from formaltask.paths import get_claude_home

COMMAND_NAME = "doctor"
COMMAND_HELP = "Check formaltask health"

# Required Claude Code hooks and their runner paths (relative to repo root)
REQUIRED_HOOKS = {
    "Stop": "hooks/stop/runner.py",
    "SessionStart": "hooks/session_start/runner.py",
    "PreToolUse": "hooks/pretool/runner.py",
    "PostToolUse": "hooks/posttool/runner.py",
    "UserPromptSubmit": "hooks/promptsubmit/runner.py",
}


# STUB: No arguments - command takes no options
def setup_parser(subparser):
    """No arguments needed."""


def _check_hook_configured(hooks: dict, hook_name: str, runner_path: str) -> str | None:
    """Check if a hook calls the correct runner. Returns None if OK, or error string."""
    if hook_name not in hooks:
        return "not registered"
    matchers = hooks[hook_name]
    if not matchers:
        return "no matchers"
    for matcher in matchers:
        for hook in matcher.get("hooks", []):
            cmd = hook.get("command", "")
            if runner_path not in cmd:
                continue
            for part in cmd.split():
                if runner_path not in part:
                    continue
                if Path(part).exists():
                    return None
                return f"runner not found: {part}"
    return f"not pointing to {runner_path}"


def execute(args) -> int:
    """Check Python, git hooks, Claude Code hooks, and database."""
    ok = True

    # Python 3.11+
    major, minor = sys.version_info[:2]
    print(f"✓ Python {major}.{minor}")

    # Git hooks path = .githooks
    try:
        result = subprocess.run(
            ["git", "config", "core.hooksPath"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        hooks_path = result.stdout.strip()
        if hooks_path == ".githooks":
            print("✓ Git hooks (.githooks)")
        elif hooks_path:
            print(f"✗ Git hooks: '{hooks_path}' (need .githooks)")
            ok = False
        else:
            print("✗ Git hooks not configured (run: git config core.hooksPath .githooks)")
            ok = False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("✗ Git not available")
        ok = False

    # Claude Code hooks in ~/.claude/settings.json
    settings_path = get_claude_home() / "settings.json"
    if not settings_path.exists():
        print("✗ ~/.claude/settings.json missing")
        ok = False
    else:
        try:
            settings = json.loads(settings_path.read_text())
            hooks = settings.get("hooks", {})

            hook_errors = []
            for hook_name, runner_path in REQUIRED_HOOKS.items():
                error = _check_hook_configured(hooks, hook_name, runner_path)
                if error:
                    hook_errors.append(f"{hook_name}: {error}")

            if hook_errors:
                print("✗ Claude hooks:")
                for err in hook_errors:
                    print(f"    {err}")
                ok = False
            else:
                print("✓ Claude hooks (Stop, SessionStart, PreToolUse, PostToolUse, UserPromptSubmit)")
        except json.JSONDecodeError:
            print("✗ ~/.claude/settings.json invalid JSON")
            ok = False

    # Database
    from formaltask.db.path import get_db_path

    try:
        db_path = get_db_path()
    except (FileNotFoundError, ValueError) as e:
        print(f"✗ Database: {e}")
        ok = False
    else:
        try:
            conn = sqlite3.connect(str(db_path), timeout=5)
            conn.execute("SELECT 1 FROM epics LIMIT 1")
            conn.close()
            print(f"✓ Database ({db_path})")
        except sqlite3.Error as e:
            print(f"✗ Database error: {e}")
            ok = False

    return ExitCode.SUCCESS.value if ok else ExitCode.GENERAL_ERROR.value
