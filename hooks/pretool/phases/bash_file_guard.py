"""Bash file guard phase - validates file operations in bash."""

from formaltask.validators.bash_file_guard import check as _check


def check(ctx: dict) -> dict | None:
    """Validate file operations in bash commands.

    Delegates to formaltask.validators.bash_file_guard.check() which returns:
    - None if allowed
    - {"decision": "block", "reason": str} if blocked
    """
    result = _check(ctx)
    if result and result.get("decision") == "block":
        return result
    return None
