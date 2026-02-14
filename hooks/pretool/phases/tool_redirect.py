"""Tool redirect phase - redirects tools based on rules kernel (Task #2881)."""

from formaltask.validators.tool_redirect import check as _check


def check(ctx: dict) -> dict | None:
    """Check if tool should be redirected based on rules.

    Delegates to formaltask.validators.tool_redirect.check() which returns:
    - None for tools not matching any redirect rules
    - {"decision": "block", "reason": str} for matched tools
    """
    result = _check(ctx)
    if result and result.get("decision") == "block":
        return result
    return None
