from __future__ import annotations

import argparse
import functools
from dataclasses import dataclass

__all__ = ["CLIContext", "with_repository", "with_db_path"]


@dataclass(frozen=True, slots=True)
class CLIContext:
    """Immutable context for CLI commands."""

    db_path: str

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> CLIContext:
        """Create CLIContext from parsed arguments."""
        db_path = resolve_db_path(args)
        return cls(db_path=db_path)


def resolve_db_path(args: argparse.Namespace) -> str:
    """Resolve database path from args or default."""
    if getattr(args, "db_path", None):
        from formaltask.db.path import validate_user_db_path

        return str(validate_user_db_path(args.db_path))
    from formaltask.db.path import get_db_path

    return str(get_db_path())


def _handle_db_error(e: Exception) -> int:
    """Print DB resolution error and return exit code 1."""
    if isinstance(e, FileNotFoundError):
        print(f"Error: Database not found - {e}")
        print("  Ensure you're in a project with .claude/formaltask.db")
    else:
        print(f"Error: Invalid --db-path: {e}")
    return 1


def with_repository(func):
    """Inject CLIContext as first argument."""

    @functools.wraps(func)
    def wrapper(args: argparse.Namespace) -> int:
        try:
            ctx = CLIContext.from_args(args)
        except (FileNotFoundError, ValueError) as e:
            return _handle_db_error(e)
        return func(ctx, args)

    return wrapper


def with_db_path(func):
    """Inject resolved db_path as first argument."""

    @functools.wraps(func)
    def wrapper(args: argparse.Namespace) -> int:
        try:
            db_path = resolve_db_path(args)
        except (FileNotFoundError, ValueError) as e:
            return _handle_db_error(e)
        return func(db_path, args)

    return wrapper
