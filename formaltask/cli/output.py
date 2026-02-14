"""OutputFormatter for multi-mode CLI output.

Handles JSON, human-readable, and NDJSON streaming output modes.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from formaltask.cli.base import CLIError


class FormatterArgs(Protocol):
    """Protocol for arguments passed to OutputFormatter."""

    json: bool
    stream: bool


def _json_fallback(obj):
    """Fallback serializer for non-serializable objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__dict__") and obj.__dict__:
        return obj.__dict__
    return repr(obj)


class OutputFormatter:
    """Multi-mode output formatter for CLI responses."""

    def __init__(self, args: FormatterArgs):
        """Initialize formatter with mode detection from args.

        Args:
            args: Parsed command-line arguments with json/stream flags
        """
        self.json_mode = getattr(args, "json", False)
        self.stream_mode = getattr(args, "stream", False)

    def success(self, data: dict, human_template: str) -> str:
        """Format a success response."""
        if self.json_mode:
            return json.dumps({"success": True, "data": data}, default=_json_fallback)
        if self.stream_mode:
            return json.dumps({"type": "complete", "data": data}, default=_json_fallback)
        return human_template.format(**data)

    def error(self, cli_error: CLIError, request_id: str | None = None) -> str:
        """Format an error response.

        Args:
            cli_error: CLIError with message, code, and exit_code
            request_id: Optional request ID for tracing

        Returns:
            JSON or human-readable error string
        """
        if self.json_mode or self.stream_mode:
            response = {
                "success": False,
                "error": {
                    "message": cli_error.message,
                    "code": cli_error.code,
                    "exit_code": cli_error.exit_code.value,
                },
            }
            if request_id:
                response["request_id"] = request_id
            return json.dumps(response)
        return f"Error: {cli_error.message}"
