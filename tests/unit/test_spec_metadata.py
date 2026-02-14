"""Tests for spec metadata validation schema.

Tests Pydantic validation for artifact_type/artifact_content fields,
including co-presence validation, 64KB size limit, and type validation.
"""

import pytest
from pydantic import ValidationError


def test_spec_metadata_requires_content_when_type_provided():
    """When artifact_type is provided, artifact_content must also be provided."""
    from formaltask.utils.schemas import SpecMetadata

    with pytest.raises(ValidationError) as exc_info:
        SpecMetadata(artifact_type="spec")

    errors = exc_info.value.errors()
    assert any("artifact_content" in str(e) for e in errors)


def test_spec_metadata_requires_type_when_content_provided():
    """When artifact_content is provided, artifact_type must also be provided."""
    from formaltask.utils.schemas import SpecMetadata

    with pytest.raises(ValidationError) as exc_info:
        SpecMetadata(artifact_content="Some spec content here")

    errors = exc_info.value.errors()
    assert any("artifact_type" in str(e) for e in errors)


def test_spec_metadata_valid_with_both_fields():
    """Both artifact_type and artifact_content provided is valid."""
    from formaltask.utils.schemas import SpecMetadata

    metadata = SpecMetadata(artifact_type="spec", artifact_content="## Goal\nImplement feature X")
    assert metadata.artifact_type == "spec"
    assert metadata.artifact_content == "## Goal\nImplement feature X"


def test_spec_metadata_rejects_content_over_64kb():
    """Metadata content exceeding 64KB should be rejected."""
    from formaltask.utils.schemas import SpecMetadata

    # 64KB = 65536 bytes, so 65537 is just over the limit
    large_content = "A" * 65537

    with pytest.raises(ValidationError) as exc_info:
        SpecMetadata(artifact_type="spec", artifact_content=large_content)

    # Verify error message mentions size limit clearly
    error_msg = str(exc_info.value)
    assert "64KB" in error_msg or "exceeds" in error_msg.lower()


@pytest.mark.parametrize("invalid_type", ["INVALID", "PRP", "INITIAL"])
def test_spec_metadata_rejects_invalid_artifact_types(invalid_type):
    """artifact_type must be 'spec'; PRP and INITIAL are no longer valid."""
    from formaltask.utils.schemas import SpecMetadata

    with pytest.raises(ValidationError) as exc_info:
        SpecMetadata(artifact_type=invalid_type, artifact_content="content")

    errors = exc_info.value.errors()
    assert any("artifact_type" in str(e) for e in errors)


def test_spec_metadata_valid_with_empty_both_fields():
    """Both fields omitted (None) is valid."""
    from formaltask.utils.schemas import SpecMetadata

    metadata = SpecMetadata()
    assert metadata.artifact_type is None
    assert metadata.artifact_content is None


def test_spec_metadata_size_limit_counts_bytes_not_characters():
    """Size limit should count UTF-8 bytes, not characters.

    CJK characters are 3 bytes each in UTF-8. 21846 characters * 3 = 65538 bytes,
    which exceeds the 64KB (65536 byte) limit even though character count is under.
    """
    from formaltask.utils.schemas import SpecMetadata

    # 21846 CJK characters = 65538 bytes (just over 64KB)
    large_cjk = "\u4e00" * 21846

    with pytest.raises(ValidationError) as exc_info:
        SpecMetadata(artifact_type="spec", artifact_content=large_cjk)

    error_msg = str(exc_info.value)
    assert "64" in error_msg or "size" in error_msg.lower() or "exceeds" in error_msg.lower()


def test_spec_metadata_accepts_exactly_64kb():
    """Content at exactly 64KB boundary should be valid."""
    from formaltask.utils.schemas import SpecMetadata

    # Exactly 65536 bytes (ASCII, 1 byte per char)
    exactly_64kb = "A" * 65536

    metadata = SpecMetadata(artifact_type="spec", artifact_content=exactly_64kb)
    assert len(metadata.artifact_content.encode("utf-8")) == 65536


def test_spec_metadata_accepts_one_byte_under_64kb():
    """Content one byte under 64KB boundary should be valid (off-by-one safety)."""
    from formaltask.utils.schemas import SpecMetadata

    # 65535 bytes (one byte under limit)
    under_64kb = "x" * 65535

    metadata = SpecMetadata(artifact_type="spec", artifact_content=under_64kb)
    assert len(metadata.artifact_content.encode("utf-8")) == 65535
