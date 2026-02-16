"""Request validation for API v2 endpoints using Pydantic."""

from pydantic import BaseModel, field_validator

VALID_STATUSES = {"open", "in_progress", "completed", "blocked", "cancelled"}
MAX_TITLE_LENGTH = 500


class TaskCreateRequest(BaseModel):
    epic_name: str
    title: str
    description: str = ""

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be empty")
        if len(v) > MAX_TITLE_LENGTH:
            raise ValueError(f"title must be at most {MAX_TITLE_LENGTH} characters")
        return v


class TaskUpdateRequest(BaseModel):
    status: str | None = None
    title: str | None = None
    description: str | None = None

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v
