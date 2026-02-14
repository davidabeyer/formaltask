"""Tests for task creation validation (Task #2396, #2711).

Task #2396: Move validation from facade to create_task.
Task #2711: TaskOperations inlined - validation now in standalone functions.
"""

import os

import pytest

from formaltask.utils.validation import validate_task_creation


def test_create_task_validates_mini_spec_metadata(db_path, repo):
    """create_task should validate MiniSpec metadata when artifact fields present."""
    from pydantic import ValidationError

    repo.create_epic("test-epic", "Test epic")

    # artifact_type without artifact_content should fail validation
    with pytest.raises(ValidationError, match="artifact_content"):
        repo.create_task(
            epic_name="test-epic",
            title="Test Task",
            description="Description",
            criteria=["Criterion"],
            metadata={"artifact_type": "spec"},  # Missing artifact_content
        )


def test_create_task_validates_empty_criteria(db_path, repo):
    """create_task should validate empty criteria."""
    repo.create_epic("test-epic", "Test epic")

    # Should still validate empty criteria
    with pytest.raises(ValueError, match="At least 1 criterion required"):
        repo.create_task(
            epic_name="test-epic",
            title="Test Task",
            description="Description",
            criteria=[],  # Empty criteria should fail
        )


def test_create_tasks_batch_validates_mini_spec_metadata(db_path, repo):
    """Batch creation should validate MiniSpec metadata like single create."""
    from pydantic import ValidationError

    from formaltask.tasks.crud import create_tasks_batch

    repo.create_epic("test-epic", "Test epic")

    # Batch with invalid artifact metadata should fail
    tasks = [
        {
            "title": "Task 1",
            "description": "Description",
            "criteria": ["Criterion"],
            "metadata": {"artifact_type": "spec"},  # Missing artifact_content
        }
    ]

    with pytest.raises(ValidationError, match="artifact_content"):
        create_tasks_batch(db_path, "test-epic", tasks)


def test_validate_task_creation_accepts_completion_rules_only(monkeypatch):
    """completion_rules is a valid alternative to required_reviews."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    # Should NOT raise — completion_rules is sufficient
    validate_task_creation(
        title="Blocker task",
        description="Fix CI",
        criteria=["CI passes"],
        metadata={"completion_rules": {"require_pr": True}},
    )


def test_validate_task_creation_rejects_no_review_config(monkeypatch):
    """Metadata without required_reviews or completion_rules should fail."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    with pytest.raises(ValueError, match="required_reviews or completion_rules"):
        validate_task_creation(
            title="Bad task",
            description="Missing review config",
            criteria=["Something"],
            metadata={"some_key": "value"},
        )


def test_validate_task_creation_rejects_no_metadata(monkeypatch):
    """None metadata should fail outside tests."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    with pytest.raises(ValueError, match="required_reviews or completion_rules"):
        validate_task_creation(
            title="Bad task",
            description="No metadata",
            criteria=["Something"],
            metadata=None,
        )
