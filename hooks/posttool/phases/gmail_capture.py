"""Capture Gmail sends to prospect database.

PostToolUse phase that automatically records outreach when emails
are sent via Composio Gmail MCP. Fails open (logs errors, doesn't block).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Add life project for imports
_life_root = str(Path.home() / "life")
if _life_root not in sys.path:
    sys.path.insert(0, _life_root)


def capture_gmail_send(ctx: dict) -> None:
    """Capture Gmail send to prospect database.

    Intercepts GMAIL_SEND_EMAIL calls via MCP gateway and records
    the outreach in CozoDB if the recipient is a known prospect.

    Args:
        ctx: PostToolUse context with tool_name, tool_input, tool_result
    """
    tool_name = ctx.get("tool_name", "")

    # Match both direct MCP tool and gateway-wrapped calls
    if "GMAIL_SEND_EMAIL" not in tool_name.upper() and "gmail" not in tool_name.lower():
        return

    # Gateway wraps as mcp__gateway__call_mcp_tool with nested structure
    tool_input = ctx.get("tool_input", {})

    # Handle gateway wrapper: tool_input = {tool_name: "...", tool_input: {...}}
    if "tool_name" in tool_input and "GMAIL_SEND_EMAIL" in tool_input.get("tool_name", "").upper():
        inner_input = tool_input.get("tool_input", {})
    else:
        inner_input = tool_input

    # Extract email details
    recipient = (
        inner_input.get("recipient_email") or inner_input.get("to") or inner_input.get("recipient")
    )
    subject = inner_input.get("subject", "")

    if not recipient:
        logger.debug("gmail_capture: No recipient found in payload")
        return

    # Check if send succeeded
    tool_result = ctx.get("tool_result", {})
    # Gateway returns nested: {result: {success: true, ...}}
    if isinstance(tool_result, dict):
        result_inner = tool_result.get("result", tool_result)
        if isinstance(result_inner, dict) and result_inner.get("success") is False:
            logger.debug("gmail_capture: Email send failed, not recording")
            return

    # Lookup and record
    try:
        from db.prospect import get_prospect_by_email, mark_email_sent

        prospect = get_prospect_by_email(recipient)
        if not prospect:
            logger.warning(
                "gmail_capture: Sent email to %s but no matching prospect found", recipient
            )
            return

        mark_email_sent(prospect["id"], subject)
        logger.info("gmail_capture: Recorded outreach to %s (%s)", prospect["name"], recipient)

    except Exception as e:
        # Fail open: email was sent, just logging failed
        logger.error("gmail_capture: Failed to record outreach: %s", e)
