"""SQL guard phase - blocks write SQL to formaltask.db."""

from formaltask.validators.sql_guard import check as _check


def check(ctx: dict) -> dict | None:
    """Check for dangerous SQL operations on formaltask.db.

    Delegates to formaltask.validators.sql_guard.check() which returns:
    - None if allowed
    - {"decision": "block", "reason": str} if blocked
    """
    result = _check(ctx)
    if result and result.get("decision") == "block":
        return result
    return None
