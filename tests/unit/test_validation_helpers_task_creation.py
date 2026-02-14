"""Tests for validate_task_creation in validation_helpers.

TDD tests for centralized task creation validation function.
"""

import pytest

from formaltask.utils.validation import validate_task_creation


class TestValidateTaskCreation:
    """Tests for validate_task_creation function."""

    def test_empty_criteria_raises_error(self):
        """Empty criteria list raises ValueError."""
        with pytest.raises(ValueError, match="At least 1 criterion required"):
            validate_task_creation(
                title="Test task",
                description="Test description",
                criteria=[],
            )

    def test_title_exceeding_limit_raises_error(self):
        """Title exceeding 1KB raises ValueError."""
        long_title = "x" * 1025  # Just over 1KB
        with pytest.raises(ValueError, match="title exceeds maximum length"):
            validate_task_creation(
                title=long_title,
                description="Test description",
                criteria=["Criterion 1"],
            )

    def test_description_exceeding_limit_raises_error(self):
        """Description exceeding 64KB raises ValueError."""
        long_desc = "x" * 65537  # Just over 64KB
        with pytest.raises(ValueError, match="description exceeds maximum length"):
            validate_task_creation(
                title="Test task",
                description=long_desc,
                criteria=["Criterion 1"],
            )

    def test_criterion_exceeding_limit_raises_error(self):
        """Single criterion exceeding 4KB raises ValueError."""
        long_criterion = "x" * 4097  # Just over 4KB
        with pytest.raises(ValueError, match="criterion 1 exceeds maximum length"):
            validate_task_creation(
                title="Test task",
                description="Test description",
                criteria=[long_criterion],
            )

    def test_metadata_exceeding_limit_raises_error(self):
        """Metadata exceeding 64KB raises ValueError."""
        large_metadata = {"data": "x" * 65536}  # Over 64KB when serialized
        with pytest.raises(ValueError, match="metadata exceeds maximum size"):
            validate_task_creation(
                title="Test task",
                description="Test description",
                criteria=["Criterion 1"],
                metadata=large_metadata,
            )

    def test_valid_inputs_pass_validation(self):
        """Valid inputs do not raise any errors."""
        validate_task_creation(
            title="Valid task title",
            description="Valid description",
            criteria=["Criterion 1", "Criterion 2"],
            metadata={"key": "value"},
        )


class TestRequiredReviewsValidation:
    """Tests for required_reviews metadata validation in production mode.

    Task #2361: Empty list [] means explicit opt-out ("none"), not missing.
    """

    def test_empty_required_reviews_is_valid_not_missing(self, monkeypatch):
        """Empty required_reviews [] is explicit opt-out, should NOT fail validation.

        Bug: validation used `if not metadata.get(k)` which treats [] as missing.
        Fix: Use `if metadata.get(k) is None` to only fail when key is absent.
        """
        # Remove PYTEST_CURRENT_TEST to enable production validation path
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        # Empty list = explicit opt-out via "Required reviews: none"
        # This should pass validation
        validate_task_creation(
            title="Documentation task",
            description="No code reviews needed",
            criteria=["Create docs"],
            metadata={
                "artifact_type": "spec",
                "required_reviews": [],  # Explicit opt-out, NOT missing!
            },
        )
