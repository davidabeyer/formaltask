"""Integration tests for hook registration: ft setup + ft doctor end-to-end.

Test protocol: backup settings, run ft setup, verify output, run ft doctor,
run setup again (idempotency), verify no duplicates, restore backup.
"""

import json
import sqlite3
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from formaltask.cli.commands.doctor import execute as run_doctor
from formaltask.cli.commands.setup import execute as run_setup
from formaltask.cli.exit_codes import ExitCode


def _count_hooks_for_type(settings, hook_type):
    """Count total hook entries for a given hook type."""
    matchers = settings.get("hooks", {}).get(hook_type, [])
    return sum(len(m.get("hooks", [])) for m in matchers)


@pytest.fixture()
def hook_env(tmp_path, monkeypatch):
    """Set up isolated home + project dirs with settings.json, DB, and runner stubs."""
    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()

    # settings.json
    settings_path = home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({}))

    # DB in project/.claude/
    db_dir = project / ".claude"
    db_dir.mkdir(parents=True)
    conn = sqlite3.connect(str(db_dir / "formaltask.db"))
    conn.execute("CREATE TABLE IF NOT EXISTS epics (id INTEGER PRIMARY KEY)")
    conn.close()

    # Runner stubs
    for runner in [
        "hooks/stop/runner.py",
        "hooks/session_start/runner.py",
        "hooks/pretool/runner.py",
    ]:
        path = project / runner
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# stub")

    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.chdir(project)
    monkeypatch.setattr("formaltask.paths.get_project_root", lambda: project)

    return types.SimpleNamespace(home=home, project=project, settings_path=settings_path)


def _setup_args():
    args = MagicMock()
    args.yes = True
    args.db_path = None
    return args


class TestHookRegistrationIntegration:
    """Integration: setup → doctor → idempotency → preservation → backup."""

    def test_setup_completes_without_error(self, hook_env):
        """ft setup --yes completes with SUCCESS exit code."""
        assert run_setup(_setup_args()) == ExitCode.SUCCESS

    def test_doctor_passes_after_setup(self, hook_env):
        """ft doctor passes all checks after ft setup registers hooks."""
        run_setup(_setup_args())

        def mock_git_config(cmd, **_kw):
            if cmd == ["git", "config", "core.hooksPath"]:
                r = MagicMock()
                r.stdout = ".githooks\n"
                r.returncode = 0
                return r
            return MagicMock(stdout="", returncode=1)

        with patch(
            "formaltask.cli.commands.doctor.subprocess.run",
            side_effect=mock_git_config,
        ):
            assert run_doctor(MagicMock()) == ExitCode.SUCCESS

    def test_setup_twice_does_not_duplicate_hooks(self, hook_env):
        """Running setup twice does not duplicate hook entries."""
        run_setup(_setup_args())
        run_setup(_setup_args())

        settings = json.loads(hook_env.settings_path.read_text())
        assert _count_hooks_for_type(settings, "Stop") == 1
        assert _count_hooks_for_type(settings, "SessionStart") == 1
        assert _count_hooks_for_type(settings, "PreToolUse") == 1

    def test_existing_user_hooks_preserved_after_setup(self, hook_env):
        """Existing user hooks in settings.json are preserved after setup."""
        existing = {
            "hooks": {
                "Stop": [
                    {
                        "matcher": "",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "python3 /user/custom/stop_hook.py",
                                "timeout": 3000,
                            }
                        ],
                    }
                ],
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "python3 /user/custom/bash_guard.py",
                                "timeout": 5000,
                            }
                        ],
                    }
                ],
            },
            "other_setting": "preserved_value",
        }
        hook_env.settings_path.write_text(json.dumps(existing))

        run_setup(_setup_args())

        settings = json.loads(hook_env.settings_path.read_text())

        # User's custom stop hook still present
        stop_empty = next(m for m in settings["hooks"]["Stop"] if m["matcher"] == "")
        assert "python3 /user/custom/stop_hook.py" in [h["command"] for h in stop_empty["hooks"]]

        # User's custom Bash guard still present
        bash_matcher = next(m for m in settings["hooks"]["PreToolUse"] if m["matcher"] == "Bash")
        assert "python3 /user/custom/bash_guard.py" in [h["command"] for h in bash_matcher["hooks"]]

        # Non-hook settings preserved
        assert settings["other_setting"] == "preserved_value"

        # formaltask hooks also registered
        assert "SessionStart" in settings["hooks"]

    def test_backup_file_created_during_registration(self, hook_env):
        """Backup .json.bak file created when hooks are registered."""
        run_setup(_setup_args())

        backup_files = list(hook_env.settings_path.parent.glob("settings.*.json.bak"))
        assert len(backup_files) >= 1

        # Backup is valid JSON
        backup_content = json.loads(backup_files[0].read_text())
        assert isinstance(backup_content, dict)
