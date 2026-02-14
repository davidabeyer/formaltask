"""Pydantic models for YAML spec validation.

Provides:
- SpecSpec: Spec file structure for individual task specifications
- CriterionV2: V2 format for acceptance criteria with history
- ReviewsV2: V2 format for required reviews with history
- HistoryEntry: Historical revision tracking

Includes validators for common field name mistakes.
"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class CritiqueRef(BaseModel):
    """Reference to a critique finding (legacy format).

    Unknown fields are rejected - use only documented fields.
    """

    model_config = ConfigDict(extra="forbid")

    round: int
    severity: Literal["P0", "P1", "P2"]
    note: str


class Finding(BaseModel):
    """Individual critique finding with resolution tracking."""

    priority: Literal["P0", "P1", "P2"]
    finding: str
    action: str
    resolution: Literal["fixed", "rejected", "deferred"] | None = None


class CritiqueResult(BaseModel):
    """Critique result with verdict and findings list."""

    round: int | None = None
    verdict: Literal["APPROVED", "FIX_AND_SHIP", "REVISE"]
    findings: list[Finding] = []


class HistoryEntry(BaseModel):
    """Historical revision of a criterion or review.

    Unknown fields are rejected - use only documented fields.
    """

    model_config = ConfigDict(extra="forbid")

    version: str
    text: str
    critique: CritiqueResult | CritiqueRef | None = None
    resolution: Literal["fixed", "wontfix", "deferred"] | None = None

    @field_validator("version")
    @classmethod
    def validate_version_pattern(cls, v: str) -> str:
        """version must match pattern r{N} (e.g., r1, r2, r10)."""
        if not re.match(r"^r\d+$", v):
            raise ValueError("version must match pattern r{N}")
        return v

    @model_validator(mode="after")
    def validate_resolution_requires_critique(self) -> "HistoryEntry":
        """Resolution requires critique to be present."""
        if self.resolution is not None and self.critique is None:
            raise ValueError("resolution requires critique")
        return self


class CriterionV2(BaseModel):
    """V2 format for acceptance criteria with inline history.

    Unknown fields are rejected - use only documented fields.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    current: str
    command: str | None = None
    history: list[HistoryEntry] = []

    @field_validator("id")
    @classmethod
    def validate_id_pattern(cls, v: str) -> str:
        """id must match pattern c-{N} or g-{N}."""
        if not re.match(r"^[cg]-\d+$", v):
            raise ValueError("id must match pattern c-{N} or g-{N}")
        return v

    @field_validator("current")
    @classmethod
    def validate_current_not_empty(cls, v: str) -> str:
        """current cannot be empty or whitespace-only."""
        if not v.strip():
            raise ValueError("current cannot be empty")
        return v

    @field_validator("command")
    @classmethod
    def validate_command_size(cls, v: str) -> str:
        """command cannot exceed 1KB (1024 bytes)."""
        byte_size = len(v.encode("utf-8"))
        if byte_size > 1024:
            raise ValueError(f"command exceeds 1KB limit ({byte_size} bytes)")
        return v

    @field_validator("history")
    @classmethod
    def validate_history_limit(cls, v: list[HistoryEntry]) -> list[HistoryEntry]:
        """history cannot exceed 100 entries."""
        if len(v) > 100:
            raise ValueError("history cannot exceed 100 entries")
        return v

    @model_validator(mode="after")
    def validate_unique_critique_rounds(self) -> "CriterionV2":
        """critique.round values must be unique across history entries."""
        rounds = [
            entry.critique.round
            for entry in self.history
            if entry.critique and isinstance(entry.critique, CritiqueRef)
        ]
        if len(rounds) != len(set(rounds)):
            raise ValueError("duplicate critique round in history")
        return self


class ReviewsV2(BaseModel):
    """V2 format for required reviews with inline history."""

    id: str
    current: str
    history: list[HistoryEntry] = []

    @field_validator("id")
    @classmethod
    def validate_id_pattern(cls, v: str) -> str:
        """id must match pattern r-{N}."""
        if not re.match(r"^r-\d+$", v):
            raise ValueError("id must match pattern r-{N}")
        return v


class SpecSpec(BaseModel):
    """Spec file structure for individual task specifications.

    Required fields:
        title: Task title (e.g., "Task 1: Core Parser")
        summary: Brief task summary
        context: Background context for the task
        implementation: List of implementation steps
        acceptance_criteria: List of acceptance criteria (str or CriterionV2)
        testing: List of testing requirements

    Optional fields:
        depends_on: List of task numbers this task depends on
        implements: List of goal IDs this task implements (e.g., ["g-1", "g-2"])
        skills: List of skill names required for this task
        required_reviews: List of review types required
        prompt_template: Template string for task prompt
        inputs: Dict mapping input names to values (e.g., {"schema": "$task[1].outputs.schema"})
        outputs: Dict mapping output names to file paths (e.g., {"schema": ".artifacts/schema.json"})

    Unknown fields are rejected - use only documented fields.
    """

    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str
    context: str
    implementation: list[str]
    acceptance_criteria: list[str | CriterionV2]
    testing: list[str]
    depends_on: list[int] | None = None
    implements: list[str] | None = None
    skills: list[str] | None = None
    required_reviews: list[str] | None = None
    prompt_template: str | None = None
    inputs: dict[str, str] | None = None
    outputs: dict[str, str] | None = None

    @model_validator(mode="after")
    def validate_unique_criterion_ids(self) -> "SpecSpec":
        """CriterionV2 IDs must be unique within acceptance_criteria."""
        seen: set[str] = set()
        duplicates: set[str] = set()
        for criterion in self.acceptance_criteria:
            if isinstance(criterion, CriterionV2):
                if criterion.id in seen:
                    duplicates.add(criterion.id)
                seen.add(criterion.id)
        if duplicates:
            sorted_dups = ", ".join(sorted(duplicates))
            raise ValueError(f"Duplicate criterion IDs found: {sorted_dups}")
        return self
