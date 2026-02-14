"""TDD guard phase - enforces test-first development."""

import json
import logging
import subprocess

logger = logging.getLogger(__name__)


def check(ctx: dict) -> dict | None:
    """Enforce test-first development via tdd-guard CLI."""
    tool_name = ctx.get("tool_name", "")
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return None

    try:
        result = subprocess.run(
            ["tdd-guard", "validate"],
            input=json.dumps(ctx),
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Exit code 2 means block
        if result.returncode == 2:
            reason = result.stdout.strip() or "TDD guard blocked this operation"
            return {"decision": "block", "reason": reason}

        return None
    except FileNotFoundError:
        # tdd-guard not installed, allow operation
        return None
    except subprocess.TimeoutExpired:
        # Timeout, allow operation (fail-open)
        logger.debug("tdd-guard timed out, allowing operation")
        return None
    except (OSError, json.JSONDecodeError) as e:
        # Specific errors that could occur during subprocess/JSON operations
        logger.debug("tdd-guard error, allowing operation: %s", e)
        return None
