"""Domain exceptions for formaltask."""

from __future__ import annotations


class FormaltaskError(Exception):
    """Base for all formaltask domain exceptions."""


class TaskNotFoundError(FormaltaskError):
    """Task ID doesn't exist."""

    def __init__(self, task_id: int) -> None:
        self.task_id = task_id
        super().__init__(f"Task {task_id} not found")


class EpicNotFoundError(FormaltaskError):
    """Epic doesn't exist."""

    def __init__(self, epic_name: str) -> None:
        self.epic_name = epic_name
        super().__init__(f"Epic '{epic_name}' not found")
