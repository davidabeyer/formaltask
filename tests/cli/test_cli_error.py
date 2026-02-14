"""Unit tests for CLIError class.

Tests the CLIError class with message and exit_code attributes.
"""

from __future__ import annotations

from formaltask.cli.base import CLIError
from formaltask.cli.exit_codes import ExitCode


def test_backward_compat_message_only() -> None:
    """CLIError("msg") works, code and exit_code default to GENERAL_ERROR."""
    e = CLIError("something failed")
    assert e.message == "something failed"
    assert str(e) == "something failed"
    assert e.code == "GENERAL_ERROR"
    assert e.exit_code == ExitCode.GENERAL_ERROR


def test_cli_error_with_explicit_exit_code() -> None:
    """CLIError accepts explicit exit_code."""
    e = CLIError("not found", exit_code=ExitCode.NOT_FOUND)
    assert e.message == "not found"
    assert e.exit_code == ExitCode.NOT_FOUND


def test_cli_error_with_code() -> None:
    """CLIError accepts code parameter for structured error codes (Task #2414)."""
    e = CLIError("not found", code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)
    assert e.message == "not found"
    assert e.code == "NOT_FOUND"
    assert e.exit_code == ExitCode.NOT_FOUND
