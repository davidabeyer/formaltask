"""Tests for ft doctor command."""

import json
from unittest.mock import MagicMock, patch


class TestPluginDiscovery:
    """Tests for plugin interface compliance."""

    def test_doctor_discovered_by_plugin_system(self):
        """ft doctor is discovered by the plugin system."""
        from formaltask.cli.commands import discover_plugins

        plugins = discover_plugins()
        assert "doctor" in plugins


class TestExecute:
    """Tests for execute() behavior."""

    def test_all_pass_returns_success(self, tmp_path):
        """Return SUCCESS when all checks pass."""
        import sqlite3

        from formaltask.cli.commands.doctor import execute
        from formaltask.cli.exit_codes import ExitCode

        # Setup database
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        db_path = claude_dir / "formaltask.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE epics (id INTEGER)")
        conn.close()

        # Setup hooks directory with runner files
        hooks_dir = tmp_path / "hooks"
        (hooks_dir / "stop").mkdir(parents=True)
        (hooks_dir / "session_start").mkdir(parents=True)
        (hooks_dir / "pretool").mkdir(parents=True)
        (hooks_dir / "stop" / "runner.py").write_text("")
        (hooks_dir / "session_start" / "runner.py").write_text("")
        (hooks_dir / "pretool" / "runner.py").write_text("")

        # Setup settings.json with required hooks pointing to runners
        home_claude = tmp_path / "home" / ".claude"
        home_claude.mkdir(parents=True)
        settings = {
            "hooks": {
                "Stop": [{"hooks": [{"command": f"python3 {tmp_path}/hooks/stop/runner.py"}]}],
                "SessionStart": [
                    {"hooks": [{"command": f"python3 {tmp_path}/hooks/session_start/runner.py"}]}
                ],
                "PreToolUse": [
                    {"hooks": [{"command": f"python3 {tmp_path}/hooks/pretool/runner.py"}]}
                ],
            }
        }
        (home_claude / "settings.json").write_text(json.dumps(settings))

        # Mock git config
        mock_result = MagicMock()
        mock_result.stdout = ".githooks\n"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("formaltask.cli.commands.doctor.Path") as mock_path,
        ):

            def path_side_effect(p):
                if p == ".claude/formaltask.db":
                    return db_path
                return tmp_path / p

            mock_path.side_effect = path_side_effect
            mock_path.home.return_value = tmp_path / "home"

            result = execute(None)
            assert result == ExitCode.SUCCESS

    def test_hooks_not_configured_returns_error(self):
        """Return GENERAL_ERROR when git hooks not configured."""
        from formaltask.cli.commands.doctor import execute
        from formaltask.cli.exit_codes import ExitCode

        mock_result = MagicMock()
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = execute(None)
            assert result == ExitCode.GENERAL_ERROR

    def test_missing_claude_hooks_returns_error(self, tmp_path):
        """Return GENERAL_ERROR when Claude Code hooks missing."""
        from formaltask.cli.commands.doctor import execute
        from formaltask.cli.exit_codes import ExitCode

        # Setup settings.json missing required hooks
        home_claude = tmp_path / ".claude"
        home_claude.mkdir(parents=True)
        settings = {"hooks": {"Stop": [{}]}}  # Missing SessionStart, PreToolUse
        (home_claude / "settings.json").write_text(json.dumps(settings))

        mock_result = MagicMock()
        mock_result.stdout = ".githooks\n"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            result = execute(None)
            assert result == ExitCode.GENERAL_ERROR

    def test_no_database_returns_error(self, tmp_path, monkeypatch):
        """Return GENERAL_ERROR when database missing."""
        from formaltask.cli.commands.doctor import execute
        from formaltask.cli.exit_codes import ExitCode

        # Setup settings.json in home
        home_claude = tmp_path / "home" / ".claude"
        home_claude.mkdir(parents=True)
        settings = {"hooks": {"Stop": [{}], "SessionStart": [{}], "PreToolUse": [{}]}}
        (home_claude / "settings.json").write_text(json.dumps(settings))

        # Change to a directory without .claude/formaltask.db
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        monkeypatch.chdir(work_dir)

        mock_result = MagicMock()
        mock_result.stdout = ".githooks\n"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.home", return_value=tmp_path / "home"),
        ):
            result = execute(None)
            assert result == ExitCode.GENERAL_ERROR
