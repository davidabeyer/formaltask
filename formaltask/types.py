"""Type definitions for repository returns."""

from typing import Any, TypedDict


class TaskData(TypedDict):
    id: int
    epic_name: str
    title: str
    description: str | None
    status: str
    position: int
    depends_on: str | None
    created_at: str
    started_at: str | None
    completed_at: str | None
    is_parallel: bool
    metadata: dict[str, Any] | None
    artifacts_json: str | None


class EpicData(TypedDict):
    name: str
    description: str | None
    skip_review: bool | None
    created_at: str
    archived_at: str | None


class CriticalPathResult(TypedDict):
    length: int
    path: list[int]


class FileHotspot(TypedDict):
    file: str
    task_ids: list[int]


class TaskListItem(TypedDict):
    id: int
    title: str
    status: str
