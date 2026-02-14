"""Doc guard phase - validates file paths against information architecture rules.

Blocks deprecated path patterns and suggests correct locations.
"""

from formaltask.validators.pre_tool_use import check as _check


def check(ctx: dict) -> dict | None:
    """Validate file paths against information architecture rules.

    Delegates to formaltask.validators.pre_tool_use.check() which returns:
    - None if allowed
    - {"decision": "block", "reason": str} if blocked
    """
    result = _check(ctx)
    if result and result.get("decision") == "block":
        return result
    return None
