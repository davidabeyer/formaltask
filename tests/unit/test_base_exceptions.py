"""Unit tests for formaltask.exceptions."""

from __future__ import annotations


class TestTaskNotFoundError:
    """Tests for TaskNotFoundError."""

    def test_stores_task_id(self) -> None:
        """TaskNotFoundError stores task_id attribute."""
        from formaltask.exceptions import TaskNotFoundError

        exc = TaskNotFoundError(42)
        assert exc.task_id == 42

    def test_str_contains_task_id(self) -> None:
        """str(TaskNotFoundError) includes task ID."""
        from formaltask.exceptions import TaskNotFoundError

        exc = TaskNotFoundError(42)
        assert "42" in str(exc)


class TestEpicNotFoundError:
    """Tests for EpicNotFoundError."""

    def test_stores_epic_name(self) -> None:
        """EpicNotFoundError stores epic_name attribute."""
        from formaltask.exceptions import EpicNotFoundError

        exc = EpicNotFoundError("my-epic")
        assert exc.epic_name == "my-epic"

    def test_str_contains_epic_name(self) -> None:
        """str(EpicNotFoundError) includes epic name."""
        from formaltask.exceptions import EpicNotFoundError

        exc = EpicNotFoundError("my-epic")
        assert "my-epic" in str(exc)
