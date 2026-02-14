"""Schema for Claude Code PreToolUse hook input data.

This module defines the Pydantic schema for validating hook input,
based on observed real Claude Code hook invocations.
"""

from pydantic import BaseModel, ConfigDict


class PreToolUseHookData(BaseModel):
    """Schema for PreToolUse hook input data.

    Finalized schema based on analysis of 21 captured samples (Task #1696).

    Required fields (present in ALL samples):
        tool_name: Name of the tool being invoked (e.g., "Bash", "Read", "Edit")
        tool_input: Dictionary of tool-specific parameters

    The schema uses extra="allow" to accommodate any future fields Claude Code
    may add without breaking existing validators.
    """

    model_config = ConfigDict(extra="allow")

    tool_name: str
    tool_input: dict
