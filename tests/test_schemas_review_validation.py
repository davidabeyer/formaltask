"""Tests for REVIEW_TYPE_AGENTS enhancement and _validate_reviews_list helper.

Task #2829: Validates new entries (spec-critique, epic-critique, merge-resolution),
invocation/instruction fields, and extracted validation helper.
"""

import pytest


class TestReviewTypeAgentsEntries:
    """Test REVIEW_TYPE_AGENTS has required entries and fields."""

    def test_spec_critique_entry_exists(self):
        """AC: spec-critique in REVIEW_TYPE_AGENTS."""
        from formaltask.utils.schemas import REVIEW_TYPE_AGENTS

        assert "spec-critique" in REVIEW_TYPE_AGENTS

    def test_epic_critique_entry_exists(self):
        """AC: epic-critique in REVIEW_TYPE_AGENTS."""
        from formaltask.utils.schemas import REVIEW_TYPE_AGENTS

        assert "epic-critique" in REVIEW_TYPE_AGENTS

    def test_merge_resolution_entry_exists(self):
        """AC: merge-resolution in REVIEW_TYPE_AGENTS."""
        from formaltask.utils.schemas import REVIEW_TYPE_AGENTS

        assert "merge-resolution" in REVIEW_TYPE_AGENTS


class TestReviewTypeAgentsInvocationField:
    """Test invocation field exists on entries."""

    def test_code_quality_has_invocation_field(self):
        """AC: REVIEW_TYPE_AGENTS['code-quality'].get('invocation') returns Task invocation."""
        from formaltask.utils.schemas import REVIEW_TYPE_AGENTS

        invocation = REVIEW_TYPE_AGENTS["code-quality"].get("invocation")
        assert invocation is not None
        assert "Task" in invocation
        assert "code-reviewer" in invocation

    def test_spec_critique_has_invocation_field(self):
        """New entry has invocation field."""
        from formaltask.utils.schemas import REVIEW_TYPE_AGENTS

        invocation = REVIEW_TYPE_AGENTS["spec-critique"].get("invocation")
        assert invocation is not None
        assert "Skill" in invocation


class TestReviewTypeAgentsInstructionField:
    """Test instruction field exists on entries."""

    def test_code_quality_has_instruction_field(self):
        """code-quality has instruction field."""
        from formaltask.utils.schemas import REVIEW_TYPE_AGENTS

        instruction = REVIEW_TYPE_AGENTS["code-quality"].get("instruction")
        assert instruction is not None
        assert len(instruction) > 10  # Non-trivial instruction


class TestValidateReviewsListHelper:
    """Test _validate_reviews_list helper function."""

    def test_valid_review_types_succeed(self):
        """AC: _validate_reviews_list(['code-quality']) succeeds."""
        from formaltask.utils.schemas import _validate_reviews_list

        result = _validate_reviews_list(["code-quality"])
        assert result == ["code-quality"]

    def test_multiple_valid_types_succeed(self):
        """Multiple valid types pass validation."""
        from formaltask.utils.schemas import _validate_reviews_list

        result = _validate_reviews_list(["code-quality", "security", "spec-critique"])
        assert result == ["code-quality", "security", "spec-critique"]

    def test_none_input_returns_none(self):
        """None input returns None."""
        from formaltask.utils.schemas import _validate_reviews_list

        result = _validate_reviews_list(None)
        assert result is None

    def test_empty_list_returns_empty_list(self):
        """Empty list is valid (no reviews required)."""
        from formaltask.utils.schemas import _validate_reviews_list

        result = _validate_reviews_list([])
        assert result == []

    def test_invalid_review_type_raises_value_error(self):
        """AC: _validate_reviews_list(['nonexistent']) raises ValueError."""
        from formaltask.utils.schemas import _validate_reviews_list

        with pytest.raises(ValueError, match="nonexistent"):
            _validate_reviews_list(["nonexistent"])

    def test_mixed_valid_invalid_raises_value_error(self):
        """Mix of valid and invalid raises ValueError."""
        from formaltask.utils.schemas import _validate_reviews_list

        with pytest.raises(ValueError, match="bad-type"):
            _validate_reviews_list(["code-quality", "bad-type"])
