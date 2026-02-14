"""Tests for cli_context.py - CLI context management for FormalTask commands.

TDD: Tests written FIRST before implementation (Task #1947).
Task #2723: Updated to reflect CLIContext only having db_path (no repo field).
"""

import argparse
from unittest.mock import patch

import pytest


class TestResolveDbPath:
    """Tests for resolve_db_path() function."""

    def test_uses_args_db_path_when_present(self):
        """Should return validated args.db_path when it's set."""
        from formaltask.cli.context import resolve_db_path

        args = argparse.Namespace(db_path="/custom/path.db")
        with patch("formaltask.db.path.validate_user_db_path") as mock:
            mock.return_value = "/custom/path.db"
            assert resolve_db_path(args) == "/custom/path.db"
            mock.assert_called_once_with("/custom/path.db")

    def test_falls_back_to_get_db_path(self):
        """Should call get_db_path() when args.db_path is None."""
        from formaltask.cli.context import resolve_db_path

        args = argparse.Namespace(db_path=None)
        with patch("formaltask.db.path.get_db_path") as mock:
            mock.return_value = "/default/path.db"
            result = resolve_db_path(args)
            assert result == "/default/path.db"
            mock.assert_called_once()

    def test_handles_missing_attribute(self):
        """Should handle args without db_path attribute (getattr fallback)."""
        from formaltask.cli.context import resolve_db_path

        args = argparse.Namespace()  # No db_path attribute
        with patch("formaltask.db.path.get_db_path") as mock:
            mock.return_value = "/fallback/path.db"
            result = resolve_db_path(args)
            assert result == "/fallback/path.db"
            mock.assert_called_once()

    def test_validates_user_db_path(self):
        """Should validate user-provided db_path with validate_user_db_path."""
        from formaltask.cli.context import resolve_db_path

        args = argparse.Namespace(db_path="/user/provided/path.db")
        with patch("formaltask.db.path.validate_user_db_path") as mock:
            mock.return_value = "/validated/path.db"
            result = resolve_db_path(args)
            assert result == "/validated/path.db"
            mock.assert_called_once_with("/user/provided/path.db")


class TestCLIContext:
    """Tests for CLIContext dataclass."""

    def test_from_args_creates_context(self):
        """from_args should create a valid CLIContext with db_path."""
        from formaltask.cli.context import CLIContext

        args = argparse.Namespace(db_path="/test.db")

        with patch("formaltask.db.path.validate_user_db_path") as mock_validate:
            mock_validate.return_value = "/test.db"

            ctx = CLIContext.from_args(args)

            assert ctx.db_path == "/test.db"

    def test_from_args_uses_fallback_when_db_path_none(self):
        """from_args should use get_db_path() when args.db_path is None."""
        from formaltask.cli.context import CLIContext

        args = argparse.Namespace(db_path=None)

        with patch("formaltask.db.path.get_db_path") as mock_path:
            mock_path.return_value = "/fallback/path.db"

            ctx = CLIContext.from_args(args)

            assert ctx.db_path == "/fallback/path.db"
            mock_path.assert_called_once()


class TestWithRepository:
    """Tests for @with_repository decorator."""

    def test_injects_context(self):
        """Decorated function should receive CLIContext as first argument."""
        from formaltask.cli.context import CLIContext, with_repository

        received_ctx = None

        @with_repository
        def sample_execute(ctx: CLIContext, args: argparse.Namespace) -> int:
            nonlocal received_ctx
            received_ctx = ctx
            return 0

        args = argparse.Namespace(db_path="/test.db")

        with patch("formaltask.db.path.validate_user_db_path") as mock_validate:
            mock_validate.return_value = "/test.db"
            result = sample_execute(args)

        assert result == 0
        assert received_ctx is not None
        assert isinstance(received_ctx, CLIContext)
        assert received_ctx.db_path == "/test.db"

    def test_does_not_catch_exceptions(self):
        """Decorator must NOT catch exceptions - preserves JSON error formatting."""
        from formaltask.cli.context import CLIContext, with_repository

        class CLIError(Exception):
            """Test CLI error."""

        @with_repository
        def raises_cli_error(ctx: CLIContext, args: argparse.Namespace) -> int:
            raise CLIError("test error")

        args = argparse.Namespace(db_path="/test.db")

        with (
            patch("formaltask.db.path.validate_user_db_path") as mock_validate,
            pytest.raises(CLIError, match="test error"),
        ):
            mock_validate.return_value = "/test.db"
            raises_cli_error(args)

    def test_passes_through_nonzero_return(self):
        """Decorator should pass through non-zero exit codes for CLI error handling."""
        from formaltask.cli.context import CLIContext, with_repository

        @with_repository
        def returns_error(ctx: CLIContext, args: argparse.Namespace) -> int:
            return 42

        args = argparse.Namespace(db_path="/test.db")

        with patch("formaltask.db.path.validate_user_db_path") as mock_validate:
            mock_validate.return_value = "/test.db"
            assert returns_error(args) == 42

    def test_handles_invalid_db_path_gracefully(self, capsys):
        """Decorator should catch ValueError from invalid db_path and return 1."""
        from formaltask.cli.context import CLIContext, with_repository

        @with_repository
        def sample_execute(ctx: CLIContext, args: argparse.Namespace) -> int:
            return 0

        args = argparse.Namespace(db_path="/invalid/symlink/path.db")

        with patch("formaltask.db.path.validate_user_db_path") as mock_validate:
            mock_validate.side_effect = ValueError("symlink not allowed")
            result = sample_execute(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Invalid --db-path" in captured.out


class TestWithDbPath:
    """Tests for @with_db_path decorator."""

    def test_injects_path(self):
        """Decorated function should receive db_path string as first argument."""
        from formaltask.cli.context import with_db_path

        received_path = None

        @with_db_path
        def sample_execute(db_path: str, args: argparse.Namespace) -> int:
            nonlocal received_path
            received_path = db_path
            return 0

        args = argparse.Namespace(db_path="/test.db")
        with patch("formaltask.db.path.validate_user_db_path") as mock_validate:
            mock_validate.return_value = "/test.db"
            result = sample_execute(args)

        assert result == 0
        assert received_path == "/test.db"

    def test_does_not_catch_exceptions(self):
        """Decorator must NOT catch exceptions - preserves JSON error formatting."""
        from formaltask.cli.context import with_db_path

        class CLIError(Exception):
            """Test CLI error."""

        @with_db_path
        def raises_cli_error(db_path: str, args: argparse.Namespace) -> int:
            raise CLIError("test error")

        args = argparse.Namespace(db_path="/test.db")

        with (
            patch("formaltask.db.path.validate_user_db_path") as mock_validate,
            pytest.raises(CLIError, match="test error"),
        ):
            mock_validate.return_value = "/test.db"
            raises_cli_error(args)

    def test_passes_through_nonzero_return(self):
        """Decorator should pass through non-zero exit codes for CLI error handling."""
        from formaltask.cli.context import with_db_path

        @with_db_path
        def returns_error(db_path: str, args: argparse.Namespace) -> int:
            return 42

        args = argparse.Namespace(db_path="/test.db")
        with patch("formaltask.db.path.validate_user_db_path") as mock_validate:
            mock_validate.return_value = "/test.db"
            assert returns_error(args) == 42

    def test_handles_invalid_db_path_gracefully(self, capsys):
        """Decorator should catch ValueError from invalid db_path and return 1."""
        from formaltask.cli.context import with_db_path

        @with_db_path
        def sample_execute(db_path: str, args: argparse.Namespace) -> int:
            return 0

        args = argparse.Namespace(db_path="/invalid/symlink/path.db")

        with patch("formaltask.db.path.validate_user_db_path") as mock_validate:
            mock_validate.side_effect = ValueError("symlink not allowed")
            result = sample_execute(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Invalid --db-path" in captured.out
