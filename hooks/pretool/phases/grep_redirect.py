"""Grep redirect phase - redirects Grep to warpgrep."""

from formaltask.validators.grep_to_warpgrep import check as _check


def check(ctx: dict) -> dict | None:
    """Redirect Grep to warpgrep for semantic search.

    Delegates to formaltask.validators.grep_to_warpgrep.check() which returns:
    - None if allowed (valid regex pattern)
    - {"decision": "block", "reason": str} if pattern is natural language
    """
    result = _check(ctx)
    if result and result.get("decision") == "block":
        return result
    return None
