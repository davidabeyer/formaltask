"""PreToolUse Hook: Validate planning YAML schema.

Validates Write to *-plan.yaml and *-spec.yaml files against
CriterionV2/ReviewsV2 Pydantic models. Blocks malformed writes
with helpful error messages.

Edit excluded because partial YAML cannot be validated.

Security model: fail-closed (block on any validation error).
"""

import re

import yaml
from pydantic import ValidationError

from formaltask.epics.models import CriterionV2

# Only validate Write - Edit/MultiEdit provide partial content, not complete YAML
TOOL_MATCH = ["Write"]

# File patterns that should be validated
FILE_PATTERNS = [
    r".*-plan\.yaml$",
    r".*-spec\.yaml$",
]


def _matches_planning_file(file_path: str) -> bool:
    """Check if file path matches planning YAML patterns."""
    return any(re.search(pattern, file_path) for pattern in FILE_PATTERNS)


def _validate_criterion(criterion: dict, index: int) -> str | None:
    """Validate a single criterion dict against CriterionV2 model.

    Returns error message if invalid, None if valid.
    """
    try:
        CriterionV2.model_validate(criterion)
        return None
    except ValidationError as e:
        errors = e.errors()
        if errors:
            first_error = errors[0]
            field = ".".join(str(loc) for loc in first_error.get("loc", []))
            msg = first_error.get("msg", "validation error")
            return f"criterion[{index}].{field}: {msg}"
        return f"criterion[{index}]: validation error"


def _validate_acceptance_criteria(criteria: list, path_context: str) -> str | None:
    """Validate acceptance_criteria list.

    Returns error message if invalid, None if valid.
    """
    for i, criterion in enumerate(criteria):
        if isinstance(criterion, dict):
            error = _validate_criterion(criterion, i)
            if error:
                return f"{path_context}acceptance_criteria.{error}"
    return None


def _extract_content(ctx: dict) -> str | None:
    """Extract content from Write tool_input.

    Only Write provides complete YAML content that can be validated.
    """
    tool_input = ctx.get("tool_input", {})
    return tool_input.get("content", "")


def check(ctx: dict) -> dict | None:
    """Validate planning YAML schema.

    Args:
        ctx: Hook context dict with tool_name and tool_input.

    Returns:
        None if allowed (valid schema or non-matching file),
        dict with decision='block' and reason if validation fails.
    """
    tool_name = ctx.get("tool_name", "")

    if tool_name not in TOOL_MATCH:
        return None

    tool_input = ctx.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path or not _matches_planning_file(file_path):
        return None

    content = _extract_content(ctx)
    if not content:
        return None

    # Parse YAML - fail closed on parse error
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        return {
            "decision": "block",
            "reason": f"BLOCKED: Invalid YAML in {file_path}\n\nParse error: {e}",
        }

    if not isinstance(data, dict):
        return None

    # Validate schema_version - default to 1 if absent (backward compat)
    schema_version = data.get("schema_version", 1)
    if schema_version != 1:
        return {
            "decision": "block",
            "reason": f"BLOCKED: Unknown schema_version: {schema_version}. Supported: [1]",
        }

    # Validate top-level acceptance_criteria (for spec files)
    if "acceptance_criteria" in data and isinstance(data["acceptance_criteria"], list):
        error = _validate_acceptance_criteria(data["acceptance_criteria"], "")
        if error:
            return {
                "decision": "block",
                "reason": f"BLOCKED: Invalid CriterionV2 in {file_path}\n\n{error}",
            }

    # Validate tasks (for epic and plan files)
    if "tasks" in data and isinstance(data["tasks"], list):
        for task_idx, task in enumerate(data["tasks"]):
            if isinstance(task, dict) and "acceptance_criteria" in task:
                criteria = task["acceptance_criteria"]
                if isinstance(criteria, list):
                    error = _validate_acceptance_criteria(criteria, f"tasks[{task_idx}].")
                    if error:
                        return {
                            "decision": "block",
                            "reason": f"BLOCKED: Invalid CriterionV2 in {file_path}\n\n{error}",
                        }

    return None
