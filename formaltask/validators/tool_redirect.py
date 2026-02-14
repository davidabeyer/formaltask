"""Tool redirect validator using rules kernel (Task #2881)."""

from formaltask.core.rules import apply_rules
from formaltask.core.rules_builtin import TOOL_REDIRECT_RULES


def check(ctx: dict) -> dict | None:
    """Check if tool should be redirected based on rules.

    Args:
        ctx: Tool context with tool_name and tool_input

    Returns:
        {"decision": "block", "reason": str} if rule matches, None otherwise
    """
    output, target = apply_rules(TOOL_REDIRECT_RULES, ctx)

    if output and target == "tool.block":
        return {"decision": "block", "reason": output}

    return None
