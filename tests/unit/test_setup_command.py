"""Tests for ft setup command."""

from unittest.mock import MagicMock, patch


class TestPluginDiscovery:
    """Tests for plugin interface compliance."""

    def test_setup_discovered_by_plugin_system(self):
        """ft setup is discovered by the plugin system."""
        from formaltask.cli.commands import discover_plugins

        plugins = discover_plugins()
        assert "setup" in plugins, f"setup not in plugins: {list(plugins.keys())}"

    def test_setup_module_has_required_exports(self):
        """Setup module has COMMAND_NAME, COMMAND_HELP, setup_parser, execute."""
        from formaltask.cli.commands import setup

        assert setup.COMMAND_NAME == "setup"
        assert isinstance(setup.COMMAND_HELP, str)
        assert len(setup.COMMAND_HELP) > 0
        assert callable(setup.setup_parser)
        assert callable(setup.execute)


class TestExecuteNonInteractive:
    """Tests for execute() with --yes flag."""

    def test_execute_yes_completes_without_prompts(self, tmp_path, monkeypatch):
        """execute() with --yes completes without interactive prompts."""
        from formaltask.cli.commands.setup import execute
        from formaltask.cli.exit_codes import ExitCode

        args = MagicMock()
        args.yes = True
        args.db_path = None

        monkeypatch.chdir(tmp_path)

        with (
            patch("formaltask.cli.commands.setup.ensure_schema_initialized"),
            patch("formaltask.cli.commands.setup.register_required_hooks", return_value=[]),
            patch("formaltask.cli.commands.doctor.execute"),
        ):
            result = execute(args)
            assert result == ExitCode.SUCCESS


class TestExecuteInteractive:
    """Tests for execute() without --yes flag (interactive mode)."""

    def test_execute_prompts_for_confirmation_without_yes(self, tmp_path, monkeypatch):
        """execute() without --yes prompts for confirmation."""
        from formaltask.cli.commands.setup import execute
        from formaltask.cli.exit_codes import ExitCode

        args = MagicMock()
        args.yes = False
        args.db_path = None

        monkeypatch.chdir(tmp_path)

        with (
            patch("formaltask.cli.commands.setup.ensure_schema_initialized"),
            patch("formaltask.cli.commands.setup.register_required_hooks", return_value=[]),
            patch("formaltask.cli.commands.doctor.execute"),
            patch("rich.prompt.Confirm.ask", return_value=True) as mock_confirm,
        ):
            result = execute(args)
            assert result == ExitCode.SUCCESS
            # Verify confirmation was requested for database init
            assert mock_confirm.call_count >= 1


class TestSetupParserArgs:
    """Tests for setup_parser argument configuration."""

    def test_setup_parser_adds_yes_flag(self):
        """setup_parser adds --yes/-y flag."""
        import argparse

        from formaltask.cli.commands.setup import setup_parser

        parser = argparse.ArgumentParser()
        setup_parser(parser)

        # Parse with --yes
        args = parser.parse_args(["--yes"])
        assert args.yes is True

        # Parse with -y
        args = parser.parse_args(["-y"])
        assert args.yes is True

        # Parse without flag
        args = parser.parse_args([])
        assert args.yes is False

    def test_setup_parser_adds_db_path_option(self):
        """setup_parser adds --db-path option."""
        import argparse

        from formaltask.cli.commands.setup import setup_parser

        parser = argparse.ArgumentParser()
        setup_parser(parser)

        args = parser.parse_args(["--db-path", "/custom/path.db"])
        assert args.db_path == "/custom/path.db"


class TestHookRegistration:
    """Tests for hook registration in setup flow."""

    def test_setup_handles_missing_settings_json(self, tmp_path, monkeypatch, capsys):
        """setup shows clear error when settings.json is missing."""
        from formaltask.cli.commands.setup import execute
        from formaltask.cli.exit_codes import ExitCode
        from formaltask.hooks.register import SettingsNotFoundError

        args = MagicMock()
        args.yes = True
        args.db_path = None

        monkeypatch.chdir(tmp_path)

        with (
            patch("formaltask.cli.commands.setup.ensure_schema_initialized"),
            patch(
                "formaltask.cli.commands.setup.register_required_hooks",
                side_effect=SettingsNotFoundError("/path/to/settings.json"),
            ),
            patch("formaltask.cli.commands.doctor.execute"),
        ):
            result = execute(args)

        # Setup should return failure
        assert result == ExitCode.CONFIG_ERROR

        # Error message should be clear
        captured = capsys.readouterr()
        assert "settings.json" in captured.out.lower() or "settings.json" in captured.err.lower()

    def test_setup_handles_permission_error(self, tmp_path, monkeypatch, capsys):
        """setup shows clear error when permission denied on settings.json."""
        from formaltask.cli.commands.setup import execute
        from formaltask.cli.exit_codes import ExitCode
        from formaltask.hooks.register import SettingsPermissionError

        args = MagicMock()
        args.yes = True
        args.db_path = None

        monkeypatch.chdir(tmp_path)

        with (
            patch("formaltask.cli.commands.setup.ensure_schema_initialized"),
            patch(
                "formaltask.cli.commands.setup.register_required_hooks",
                side_effect=SettingsPermissionError("/path/to/settings.json"),
            ),
            patch("formaltask.cli.commands.doctor.execute"),
        ):
            result = execute(args)

        # Setup should return failure
        assert result == ExitCode.CONFIG_ERROR

        # Error message should mention permission
        captured = capsys.readouterr()
        output = (captured.out + captured.err).lower()
        assert "permission" in output
