#!/usr/bin/env python3
"""Pydantic validation schemas for FormalTask JSON columns."""

import logging
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, field_validator, model_validator

from formaltask.paths import get_claude_home

logger = logging.getLogger(__name__)


# Review type configuration - single source of truth (Task #2525, Task #2829, Task #2896)
# Invocation strings are Jinja2 templates rendered with {task_id, title} context.
REVIEW_TYPE_AGENTS: dict[str, dict[str, str]] = {
    "code-quality": {
        "agent": "code-reviewer",
        "invocation": 'Task(subagent_type="code-reviewer", description="Review task #{{ task_id }}: {{ title }}")',
        "instruction": "Address any P0/P1 findings before completing.",
    },
    "test-quality": {
        "agent": "test-quality-auditor",
        "invocation": 'Task(subagent_type="test-quality-auditor", description="Audit test quality for task #{{ task_id }}: {{ title }}")',
        "instruction": "Fix test quality issues identified by the auditor.",
    },
    "security": {
        "agent": "code-reviewer",
        "invocation": 'Task(subagent_type="code-reviewer", description="Security-focused review for task #{{ task_id }}: {{ title }}")',
        "instruction": "Address all security findings before completing.",
    },
    "perf": {
        "agent": "performance-auditor",
        "invocation": 'Task(subagent_type="performance-auditor", description="Performance audit for task #{{ task_id }}: {{ title }}")',
        "instruction": "Address performance bottlenecks identified.",
    },
    "acceptance": {
        "agent": "acceptance-verifier",
        "invocation": 'Task(subagent_type="acceptance-verifier", description="Verify acceptance for task #{{ task_id }}: {{ title }}", prompt="Verify each acceptance criterion has concrete evidence:\\n{% for c in acceptance_criteria %}\\n- {{ c.text if c is mapping else c }}\\n{% endfor %}")',
        "instruction": "Ensure all acceptance criteria are met.",
    },
    "sqlite": {
        "agent": "sqlite-reviewer",
        "invocation": 'Task(subagent_type="sqlite-reviewer", description="SQLite review for task #{{ task_id }}: {{ title }}")',
        "instruction": "Address SQLite-specific issues before completing.",
    },
    "path-security": {
        "agent": "path-security-reviewer",
        "invocation": 'Task(subagent_type="path-security-reviewer", description="Path security review for task #{{ task_id }}: {{ title }}")',
        "instruction": "Fix path traversal and security issues.",
    },
    "subprocess": {
        "agent": "subprocess-reviewer",
        "invocation": 'Task(subagent_type="subprocess-reviewer", description="Subprocess review for task #{{ task_id }}: {{ title }}")',
        "instruction": "Address subprocess handling issues.",
    },
    "state-machine": {
        "agent": "state-machine-reviewer",
        "invocation": 'Task(subagent_type="state-machine-reviewer", description="State machine review for task #{{ task_id }}: {{ title }}")',
        "instruction": "Fix state transition issues identified.",
    },
    "hook": {
        "agent": "hook-reviewer",
        "invocation": 'Task(subagent_type="hook-reviewer", description="Hook review for task #{{ task_id }}: {{ title }}")',
        "instruction": "Address hook implementation issues.",
    },
    "tui": {
        "agent": "tui-reviewer",
        "invocation": 'Task(subagent_type="tui-reviewer", description="TUI review for task #{{ task_id }}: {{ title }}")',
        "instruction": "Fix TUI-related issues identified.",
    },
    "schema": {
        "agent": "schema-reviewer",
        "invocation": 'Task(subagent_type="schema-reviewer", description="Schema review for task #{{ task_id }}: {{ title }}")',
        "instruction": "Address schema validation issues.",
    },
    "error-handling": {
        "agent": "error-handling-reviewer",
        "invocation": 'Task(subagent_type="error-handling-reviewer", description="Error handling review for task #{{ task_id }}: {{ title }}")',
        "instruction": "Fix error handling deficiencies.",
    },
    "api-client": {
        "agent": "api-client-reviewer",
        "invocation": 'Task(subagent_type="api-client-reviewer", description="API client review for task #{{ task_id }}: {{ title }}")',
        "instruction": "Address API integration issues.",
    },
    "input-validation": {
        "agent": "input-validation-reviewer",
        "invocation": 'Task(subagent_type="input-validation-reviewer", description="Input validation review for task #{{ task_id }}: {{ title }}")',
        "instruction": "Fix input validation gaps.",
    },
    "configuration": {
        "agent": "configuration-auditor",
        "invocation": 'Task(subagent_type="configuration-auditor", description="Configuration audit for task #{{ task_id }}: {{ title }}")',
        "instruction": "Address configuration handling issues.",
    },
    "migration": {
        "agent": "migration-auditor",
        "invocation": 'Task(subagent_type="migration-auditor", description="Migration audit for task #{{ task_id }}: {{ title }}")',
        "instruction": "Fix backwards compatibility issues.",
    },
    "spec-critique": {
        "agent": "critique",
        "invocation": 'Skill("critique", args="task #{{ task_id }}: {{ title }}")',
        "instruction": "The critique skill will store its review. Repeat until clean.",
    },
    "epic-critique": {
        "agent": "critique",
        "invocation": 'Skill("critique", args="task #{{ task_id }}: {{ title }}")',
        "instruction": "Run critique on epic specs. Address all blockers.",
    },
    "merge-resolution": {
        "agent": "synthesis-agent",
        "invocation": 'Task(subagent_type="synthesis-agent", description="Resolve merge conflicts for task #{{ task_id }}: {{ title }}")',
        "instruction": "Synthesize conflicting changes and resolve merge issues.",
    },
    "self-critique": {
        "agent": "task-critic",
        "invocation": 'Task(subagent_type="task-critic", description="Self-critique for task #{{ task_id }}: {{ title }}")',
        "instruction": "Run self-critique. Address all P0/P1 findings before completing.",
    },
}

# Derived from REVIEW_TYPE_AGENTS keys - single source of truth
KNOWN_REVIEW_TYPES = frozenset(REVIEW_TYPE_AGENTS.keys())

# Reverse mapping: agent name -> short name (for normalization)
_AGENT_TO_SHORT_NAME: dict[str, str] = {
    config["agent"]: short_name for short_name, config in REVIEW_TYPE_AGENTS.items()
}


def normalize_review_type(review_type: str) -> str:
    """Normalize a review type to its canonical short form.

    Accepts both short names (e.g., 'sqlite') and agent names (e.g., 'sqlite-reviewer').

    Args:
        review_type: Review type string (short name or agent name)

    Returns:
        Normalized short name

    Raises:
        ValueError: If review type is unknown
    """
    # Check if it's already a valid short name
    if review_type in KNOWN_REVIEW_TYPES:
        return review_type
    # Check if it's an agent name
    if review_type in _AGENT_TO_SHORT_NAME:
        return _AGENT_TO_SHORT_NAME[review_type]
    raise ValueError(
        f"Unknown review type '{review_type}'. Valid types: {', '.join(sorted(KNOWN_REVIEW_TYPES))}"
    )


# Skills directory - scanned dynamically
_SKILLS_DIR = get_claude_home() / "skills"
_known_skills_cache: frozenset[str] | None = None


def get_known_skills() -> frozenset[str]:
    """Get known skills by scanning ~/.claude/skills/ directory.

    Scans for subdirectories (each skill is a directory).
    Results are cached as frozenset for performance.
    Returns empty frozenset on filesystem errors (logged as warning).
    """
    global _known_skills_cache
    if _known_skills_cache is not None:
        return _known_skills_cache

    skills: set[str] = set()
    try:
        if _SKILLS_DIR.exists() and _SKILLS_DIR.is_dir():
            for item in _SKILLS_DIR.iterdir():
                if item.is_dir():
                    skills.add(item.name)
    except OSError as e:
        logger.warning("Failed to scan skills directory %s: %s", _SKILLS_DIR, e)

    _known_skills_cache = frozenset(skills)
    return _known_skills_cache


def _validate_skills_list(v: list[str] | None) -> list[str] | None:
    """Validate all skill names are known."""
    if v is not None:
        known = get_known_skills()
        for skill in v:
            if skill not in known:
                raise ValueError(
                    f"Unknown skill '{skill}'. Known skills: {', '.join(sorted(known))}"
                )
    return v


def _validate_reviews_list(v: list[str] | None) -> list[str] | None:
    """Validate all review types are known."""
    if v is not None:
        for review_type in v:
            if review_type not in KNOWN_REVIEW_TYPES:
                raise ValueError(
                    f"Invalid review type '{review_type}'. "
                    f"Known types: {', '.join(sorted(KNOWN_REVIEW_TYPES))}"
                )
    return v


class TaskMetadata(BaseModel):
    """Validation schema for tasks.metadata JSON column."""

    defer_reason: str | None = None
    review_round: int | None = None
    blocked_by: list[int] | None = None
    custom_fields: dict[str, Any] | None = None
    required_reviews: list[str] | None = None
    skills: list[str] | None = None
    learnings: list[str] | None = None

    @field_validator("required_reviews")
    @classmethod
    def validate_review_types(cls, v: list[str] | None) -> list[str] | None:
        """Validate all review types are known."""
        return _validate_reviews_list(v)

    @field_validator("defer_reason")
    @classmethod
    def defer_reason_minimum_length(cls, v: str | None) -> str | None:
        """Validate defer_reason is >= 20 chars when provided."""
        if v is not None and len(v) < 20:
            raise ValueError(
                f"defer_reason must be at least 20 characters long (got {len(v)} characters)"
            )
        return v

    @field_validator("review_round")
    @classmethod
    def review_round_positive(cls, v: int | None) -> int | None:
        """Validate review_round is positive when provided."""
        if v is not None and v <= 0:
            raise ValueError(f"review_round must be greater than 0 (got {v})")
        return v

    @field_validator("learnings")
    @classmethod
    def validate_learning_length(cls, v: list[str] | None) -> list[str] | None:
        """Validate each learning is <= 200 chars."""
        if v is not None:
            for i, learning in enumerate(v):
                if len(learning) > 200:
                    raise ValueError(f"Learning {i + 1} too long ({len(learning)} chars). Max 200.")
        return v

    @field_validator("skills")
    @classmethod
    def validate_skill_names(cls, v: list[str] | None) -> list[str] | None:
        """Validate all skill names are known."""
        return _validate_skills_list(v)


class ComplexityAssessment(BaseModel):
    """Validation schema for task complexity assessment.

    Stores scope, risk, and ambiguity scores for task complexity tracking.
    """

    scope: int
    risk: int
    ambiguity: int
    total: int
    tier: str


class SpecMetadata(BaseModel):
    """Validation schema for spec metadata with artifact fields.

    When artifact_type is provided, artifact_content must also be provided
    and vice versa. Both fields are optional together.
    artifact_content has a 64KB size limit.
    Unknown fields are rejected (extra='forbid') for security.
    """

    # Backup rejection if check_unknown_fields doesn't trigger; custom validator runs first with better errors
    model_config = {"extra": "forbid"}

    artifact_type: Literal["spec"] | None = None
    artifact_content: str | None = None
    complexity: ComplexityAssessment | None = None
    required_reviews: list[str] | None = None
    skills: list[str] | None = None
    documentation_required: bool | None = None
    inputs: dict[str, str] | None = None
    outputs: dict[str, str] | None = None

    @model_validator(mode="before")
    @classmethod
    def check_unknown_fields(cls, data: Any) -> Any:
        """Provide helpful error message for unknown fields."""
        if isinstance(data, dict):
            allowed = set(cls.model_fields.keys())
            unknown = set(data.keys()) - allowed
            if unknown:
                raise ValueError(
                    f"Unknown field(s): {', '.join(sorted(unknown))}. "
                    f"Allowed fields: {', '.join(sorted(allowed))}"
                )
        return data

    # 64KB size limit in bytes
    MAX_CONTENT_SIZE: ClassVar[int] = 65536

    @field_validator("artifact_content")
    @classmethod
    def validate_content_size(cls, v: str | None) -> str | None:
        """Validate artifact_content does not exceed 64KB in UTF-8 bytes."""
        if v is not None:
            byte_size = len(v.encode("utf-8"))
            if byte_size > cls.MAX_CONTENT_SIZE:
                raise ValueError(
                    f"artifact_content exceeds 64KB size limit "
                    f"(got {byte_size} bytes, max {cls.MAX_CONTENT_SIZE})"
                )
        return v

    @field_validator("required_reviews")
    @classmethod
    def validate_review_types(cls, v: list[str] | None) -> list[str] | None:
        """Validate all review types are known."""
        return _validate_reviews_list(v)

    @field_validator("skills")
    @classmethod
    def validate_skill_names(cls, v: list[str] | None) -> list[str] | None:
        """Validate all skill names are known."""
        return _validate_skills_list(v)

    @model_validator(mode="after")
    def require_both_artifact_fields(self) -> "SpecMetadata":
        """Ensure artifact_type and artifact_content are both provided or both absent."""
        if self.artifact_type is not None and self.artifact_content is None:
            raise ValueError("artifact_content is required when artifact_type is provided")
        if self.artifact_content is not None and self.artifact_type is None:
            raise ValueError("artifact_type is required when artifact_content is provided")
        return self


class TaskTitle(BaseModel):
    """Validation schema for task titles with epic prefix enforcement.

    Validates that task titles follow the format: "{epic_name}: {description}"
    Max length: 200 characters (prevents abuse while allowing descriptive titles).
    """

    MAX_LENGTH: ClassVar[int] = 200

    value: str
    epic_name: str

    @model_validator(mode="after")
    def validate_title_format(self) -> "TaskTitle":
        """Validate task title has correct epic prefix and description."""
        # Check max length first
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"Task title cannot exceed {self.MAX_LENGTH} characters. "
                f"Got {len(self.value)} characters."
            )

        expected_prefix = f"{self.epic_name}: "
        if not self.value.startswith(expected_prefix):
            raise ValueError(f"Task title must start with '{expected_prefix}'. Got: '{self.value}'")

        description = self.value[len(expected_prefix) :]
        if not description.strip():
            raise ValueError("Task title description cannot be empty")

        return self
