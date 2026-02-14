"""PreToolUse validator for ft epic decompose command.

Validates before running:
1. Spec directory exists
2. Spec files exist with task-*.yaml pattern
3. Spec files are valid YAML and pass SpecSpec validation
"""

import re
from pathlib import Path


def validate_spec_dir(spec_dir: Path) -> str | None:
    """Validate spec directory structure and contents.

    Args:
        spec_dir: Path to spec directory

    Returns:
        Error message if validation fails, None if valid
    """
    from formaltask.epics.yaml_parser import SpecFormatError, parse_specs_dir

    try:
        parse_specs_dir(str(spec_dir))
        return None
    except SpecFormatError as e:
        return str(e)


def check(ctx: dict) -> dict | None:
    """Validate ft epic decompose prerequisites."""
    tool_name = ctx.get("tool_name", "")
    tool_input = ctx.get("tool_input", {})

    if tool_name != "Bash":
        return None

    command = tool_input.get("command", "")
    # Must be an actual ft epic decompose command
    if not re.search(r"(?:^|&&|\|)\s*ft\s+epic\s+decompose\s", command):
        return None

    # Extract spec directory path from command (second positional arg after epic_name)
    match = re.search(r"ft\s+epic\s+decompose\s+\S+\s+(\S+)", command)
    if not match:
        return None  # Let it fail naturally if malformed

    spec_dir = Path(match.group(1)).expanduser()
    if not spec_dir.is_absolute():
        spec_dir = Path.cwd() / spec_dir

    errors = []

    # 1. Spec directory exists
    if not spec_dir.exists():
        errors.append(f"Spec directory not found: {spec_dir}")
        return {"decision": "block", "reason": "\n".join(errors)}

    # 2. Must be a directory
    if not spec_dir.is_dir():
        errors.append(f"Expected directory, got file: {spec_dir}")
        return {"decision": "block", "reason": "\n".join(errors)}

    # 3. Check for spec files
    spec_files = list(spec_dir.glob("task-*-*.yaml"))
    if not spec_files:
        errors.append(f"No spec files (task-*-*.yaml) found in: {spec_dir}")
        return {"decision": "block", "reason": "\n".join(errors)}

    # 4. Validate spec directory structure and contents
    validation_error = validate_spec_dir(spec_dir)
    if validation_error:
        errors.append(validation_error)
        return {"decision": "block", "reason": "\n".join(errors)}

    return None


# Alias for backward compatibility
validate = check
