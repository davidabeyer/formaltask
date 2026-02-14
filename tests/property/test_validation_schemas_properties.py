"""Property-based tests for validation_schemas module."""

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from formaltask.utils.schemas import TaskMetadata

# Strategy for valid defer reasons (>= 20 chars)
valid_defer_reasons = st.text(min_size=20, max_size=500)

# Strategy for valid URLs
valid_urls = st.from_regex(r"https?://[a-z0-9]+\.[a-z0-9]+", fullmatch=True)


@given(defer_reason=valid_defer_reasons)
@settings(max_examples=50, deadline=None)
def test_valid_defer_reason_accepted(defer_reason):
    """Property: Defer reasons >= 20 chars are accepted."""
    assume(len(defer_reason) >= 20)

    metadata = TaskMetadata(defer_reason=defer_reason)
    assert metadata.defer_reason == defer_reason


@given(defer_reason=st.text(min_size=1, max_size=19))
@settings(max_examples=50, deadline=None)
def test_short_defer_reason_rejected(defer_reason):
    """Property: Defer reasons < 20 chars are rejected."""
    assume(len(defer_reason) < 20 and len(defer_reason) > 0)

    with pytest.raises(ValidationError):
        TaskMetadata(defer_reason=defer_reason)


# test_valid_pr_url_accepted removed - pr_url field removed in Task #2185


@given(review_round=st.integers(min_value=1, max_value=100))
@settings(max_examples=50, deadline=None)
def test_positive_review_round_accepted(review_round):
    """Property: Positive review_round values are accepted."""
    metadata = TaskMetadata(review_round=review_round)
    assert metadata.review_round == review_round
