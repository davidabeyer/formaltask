"""Tests for formaltask.hooks.register module."""

import json
from pathlib import Path


class TestRegisterHook:
    """Tests for register_hook function."""

    def test_register_hook_creates_hook_type_if_missing(self, tmp_path, monkeypatch):
        """When hook type doesn't exist in settings, register_hook creates it."""
        # Arrange: settings.json with empty hooks section
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(json.dumps({"hooks": {}}))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        from formaltask.hooks.register import register_hook

        # Act: register a Stop hook
        result = register_hook(
            hook_type="Stop",
            matcher="",
            hook_config={"type": "command", "command": "/path/to/hook.py", "timeout": 2000},
        )

        # Assert: Stop hook type created
        assert result is True
        settings = json.loads(settings_path.read_text())
        assert "Stop" in settings["hooks"]
        assert len(settings["hooks"]["Stop"]) == 1
        assert settings["hooks"]["Stop"][0]["matcher"] == ""
        assert len(settings["hooks"]["Stop"][0]["hooks"]) == 1
        assert settings["hooks"]["Stop"][0]["hooks"][0]["command"] == "/path/to/hook.py"

    def test_register_hook_creates_matcher_if_missing(self, tmp_path, monkeypatch):
        """When hook type exists but matcher doesn't, register_hook creates it."""
        # Arrange: settings.json with PreToolUse but no Bash matcher
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(
            json.dumps({"hooks": {"PreToolUse": [{"matcher": "", "hooks": []}]}})
        )

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        from formaltask.hooks.register import register_hook

        # Act: register a Bash matcher hook
        result = register_hook(
            hook_type="PreToolUse",
            matcher="Bash",
            hook_config={"type": "command", "command": "/path/to/guard.py", "timeout": 2000},
        )

        # Assert: Bash matcher created
        assert result is True
        settings = json.loads(settings_path.read_text())
        assert len(settings["hooks"]["PreToolUse"]) == 2
        bash_matcher = next(
            h for h in settings["hooks"]["PreToolUse"] if h.get("matcher") == "Bash"
        )
        assert bash_matcher["hooks"][0]["command"] == "/path/to/guard.py"

    def test_register_hook_adds_to_existing_matcher(self, tmp_path, monkeypatch):
        """When matcher exists with hooks, new hook is added to the list."""
        # Arrange: settings.json with existing Stop hook
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(
            json.dumps(
                {
                    "hooks": {
                        "Stop": [
                            {
                                "matcher": "",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "/existing/hook.py",
                                        "timeout": 1000,
                                    }
                                ],
                            }
                        ]
                    }
                }
            )
        )

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        from formaltask.hooks.register import register_hook

        # Act: register another Stop hook
        result = register_hook(
            hook_type="Stop",
            matcher="",
            hook_config={"type": "command", "command": "/new/hook.py", "timeout": 2000},
        )

        # Assert: both hooks present
        assert result is True
        settings = json.loads(settings_path.read_text())
        hooks_list = settings["hooks"]["Stop"][0]["hooks"]
        assert len(hooks_list) == 2
        assert hooks_list[0]["command"] == "/existing/hook.py"
        assert hooks_list[1]["command"] == "/new/hook.py"

    def test_register_hook_skips_if_already_registered(self, tmp_path, monkeypatch):
        """When hook with same command exists, don't add duplicate."""
        # Arrange: settings.json with hook already registered
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(
            json.dumps(
                {
                    "hooks": {
                        "Stop": [
                            {
                                "matcher": "",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "/path/to/hook.py",
                                        "timeout": 2000,
                                    }
                                ],
                            }
                        ]
                    }
                }
            )
        )

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        from formaltask.hooks.register import register_hook

        # Act: try to register same hook again
        result = register_hook(
            hook_type="Stop",
            matcher="",
            hook_config={"type": "command", "command": "/path/to/hook.py", "timeout": 2000},
        )

        # Assert: returns True but no duplicate
        assert result is True
        settings = json.loads(settings_path.read_text())
        hooks_list = settings["hooks"]["Stop"][0]["hooks"]
        assert len(hooks_list) == 1

    def test_register_hook_handles_empty_string_matcher(self, tmp_path, monkeypatch):
        """Empty string matcher works alongside specific matchers."""
        # Arrange: settings.json with Bash matcher but no empty string matcher
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Bash",
                                "hooks": [
                                    {"type": "command", "command": "/bash/hook.py", "timeout": 2000}
                                ],
                            }
                        ]
                    }
                }
            )
        )

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        from formaltask.hooks.register import register_hook

        # Act: register empty string matcher hook
        result = register_hook(
            hook_type="PreToolUse",
            matcher="",
            hook_config={"type": "command", "command": "/all/hook.py", "timeout": 2000},
        )

        # Assert: empty matcher created alongside Bash matcher
        assert result is True
        settings = json.loads(settings_path.read_text())
        assert len(settings["hooks"]["PreToolUse"]) == 2
        empty_matcher = next(h for h in settings["hooks"]["PreToolUse"] if h.get("matcher") == "")
        assert empty_matcher["hooks"][0]["command"] == "/all/hook.py"

    def test_register_hook_creates_backup_before_write(self, tmp_path, monkeypatch):
        """When modifying settings.json, backup created first."""
        # Arrange: settings.json with original content
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        original_content = {"hooks": {}, "other": "preserved"}
        settings_path.write_text(json.dumps(original_content))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        from formaltask.hooks.register import register_hook

        # Act: register a hook (triggers write)
        result = register_hook(
            hook_type="Stop",
            matcher="",
            hook_config={"type": "command", "command": "/path/to/hook.py", "timeout": 2000},
        )

        # Assert: backup file created with original content
        assert result is True
        backup_files = list(settings_path.parent.glob("settings.*.json.bak"))
        assert len(backup_files) == 1
        backup_content = json.loads(backup_files[0].read_text())
        assert backup_content == original_content


class TestRegisterRequiredHooks:
    """Tests for register_required_hooks function."""

    def test_register_required_hooks_registers_all_five(self, tmp_path, monkeypatch):
        """register_required_hooks registers Stop, SessionStart, PreToolUse, PostToolUse, UserPromptSubmit hooks."""
        # Arrange: empty settings.json
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(json.dumps({"hooks": {}}))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        from formaltask.hooks.register import register_required_hooks

        # Act
        results = register_required_hooks()

        # Assert: all five hook types registered
        assert len(results) == 5
        hook_types = [r[0] for r in results]
        assert "Stop" in hook_types
        assert "SessionStart" in hook_types
        assert "PreToolUse" in hook_types
        assert "PostToolUse" in hook_types
        assert "UserPromptSubmit" in hook_types
        assert all(r[1] == "registered" for r in results)
        settings = json.loads(settings_path.read_text())
        assert "Stop" in settings["hooks"]
        assert "SessionStart" in settings["hooks"]
        assert "PreToolUse" in settings["hooks"]
        assert "PostToolUse" in settings["hooks"]
        assert "UserPromptSubmit" in settings["hooks"]

    def test_register_required_hooks_idempotent(self, tmp_path, monkeypatch):
        """Calling register_required_hooks twice doesn't duplicate hooks."""
        # Arrange: empty settings.json
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(json.dumps({"hooks": {}}))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        from formaltask.hooks.register import register_required_hooks

        # Act: call twice
        register_required_hooks()
        results = register_required_hooks()

        # Assert: second call returns "skipped" for all hooks
        assert len(results) == 5
        assert all(r[1] == "skipped" for r in results)
        settings = json.loads(settings_path.read_text())
        assert len(settings["hooks"]["Stop"][0]["hooks"]) == 1
        assert len(settings["hooks"]["SessionStart"][0]["hooks"]) == 1
        assert len(settings["hooks"]["PreToolUse"][0]["hooks"]) == 1
        assert len(settings["hooks"]["PostToolUse"][0]["hooks"]) == 1
        assert len(settings["hooks"]["UserPromptSubmit"][0]["hooks"]) == 1
