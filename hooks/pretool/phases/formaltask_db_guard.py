"""FormalTask DB guard phase - validates canonical database path."""

from formaltask.validators.db_guard import check as _check


def check(ctx: dict) -> dict | None:
    """Check for non-canonical FormalTask database paths.

    Delegates to formaltask.validators.db_guard.check() which returns:
    - None if allowed
    - {"decision": "block", "reason": str} if blocked
    """
    result = _check(ctx)
    if result and result.get("decision") == "block":
        return result
    return None
