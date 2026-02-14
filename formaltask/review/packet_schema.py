"""ReviewPacket schema — gate for review agent output before DB insert."""

from pydantic import BaseModel, Field, field_validator

from formaltask.utils.constants import ReviewSeverity
from formaltask.utils.schemas import normalize_review_type


class ReviewPacket(BaseModel):
    task_id: int
    review_type: str
    severity: ReviewSeverity
    findings: list[dict] = []
    summary: str = Field(max_length=200)

    @field_validator("review_type", mode="before")
    @classmethod
    def normalize_review_type_field(cls, v: str) -> str:
        return normalize_review_type(v)

    @field_validator("findings", mode="after")
    @classmethod
    def validate_findings(cls, v: list[dict]) -> list[dict]:
        """Normalize and validate individual findings.

        - Reject string line values like '382-392' — must be int or null.
        - Normalize 'severity' key to 'priority' (reviewers use both).
        """
        for f in v:
            line = f.get("line")
            if line is not None and not isinstance(line, int):
                raise ValueError(f"finding line must be int or null, got: {line!r}")
            # Normalize: reviewers write "severity" but kernel reads "priority"
            if "severity" in f and "priority" not in f:
                f["priority"] = f.pop("severity")
        return v
