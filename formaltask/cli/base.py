"""Base utilities for FormalTask v5 CLI.

Provides shared error handling and validation utilities.
"""

from __future__ import annotations

from formaltask.cli.exit_codes import ExitCode


class CLIError(Exception):
    """CLI error with exit code and structured error code."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "GENERAL_ERROR",
        exit_code: ExitCode = ExitCode.GENERAL_ERROR,
    ):
        self.message = message
        self.code = code
        self.exit_code = exit_code
        super().__init__(message)
