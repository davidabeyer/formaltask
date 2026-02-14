"""Planning schema validator phase - validates CriterionV2 in planning YAML files."""

from formaltask.validators.planning_schema_validator import check as _check


def check(ctx: dict) -> dict | None:
    """Validate planning YAML schema.

    Delegates to formaltask.validators.planning_schema_validator.check() which returns:
    - None if allowed
    - {"decision": "block", "reason": str} if blocked
    """
    result = _check(ctx)
    if result and result.get("decision") == "block":
        return result
    return None
