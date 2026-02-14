"""Tests for metadata size validation.

TDD tests for Task #1848: Add metadata size validation with migration 024.
Tests validate_metadata_size() function that prevents oversized metadata
from being inserted into the database (resource exhaustion protection).
"""

import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from formaltask.utils.validation import MAX_METADATA_SIZE, validate_metadata_size


class TestMetadataSizeValidation:
    """Tests for metadata size validation."""

    def test_metadata_size_limit_enforced(self):
        """Metadata exceeding 64KB raises ValueError."""
        # Arrange: Create metadata > 65536 bytes
        large_metadata = {"data": "x" * 70000}

        # Act & Assert
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_metadata_size(large_metadata)

    def test_metadata_at_limit_allowed(self):
        """Metadata exactly at 65536 bytes is allowed."""
        # Arrange: Create metadata exactly at 65536 bytes
        # JSON serialization adds overhead: {"data": ""} is 11 bytes
        # So we need 65536 - 11 = 65525 bytes of content
        content_size = MAX_METADATA_SIZE - len('{"data": ""}')
        exact_metadata = {"data": "x" * content_size}

        # Verify we're at exactly the limit
        serialized = json.dumps(exact_metadata)
        assert len(serialized.encode("utf-8")) == MAX_METADATA_SIZE

        # Act & Assert: Should not raise
        validate_metadata_size(exact_metadata)  # No exception

    def test_metadata_none_allowed(self):
        """None metadata skips validation without error."""
        # Act & Assert: Should not raise
        validate_metadata_size(None)  # No exception

    def test_metadata_validation_uses_bytes_not_chars(self):
        """UTF-8 encoding is used for byte count.

        Note: json.dumps() escapes unicode to ASCII by default, so byte count
        equals char count for the serialized JSON. This test verifies we use
        encode('utf-8') as required, even though JSON escaping makes counts equal.
        """
        # Arrange: Create metadata with unicode that exceeds limit after JSON serialization
        # 🎉 becomes \ud83c\udf89 (12 ASCII chars) in JSON, so we need many to exceed limit
        emoji_count = 6000  # 6000 * 12 chars = 72000 chars > 65536
        unicode_metadata = {"data": "🎉" * emoji_count}

        # Verify the serialized JSON exceeds the limit
        serialized = json.dumps(unicode_metadata)
        byte_count = len(serialized.encode("utf-8"))
        assert byte_count > MAX_METADATA_SIZE

        # Act & Assert: Should reject oversized metadata
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_metadata_size(unicode_metadata)

    def test_metadata_validation_error_includes_sizes(self):
        """Error message shows actual size and limit."""
        # Arrange: Create oversized metadata
        large_metadata = {"data": "x" * 70000}
        expected_size = len(json.dumps(large_metadata).encode("utf-8"))

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            validate_metadata_size(large_metadata)

        error_msg = str(exc_info.value)
        # Should include actual size
        assert str(expected_size) in error_msg
        # Should include limit
        assert str(MAX_METADATA_SIZE) in error_msg


class TestMetadataSizePropertyTests:
    """Property-based tests for metadata size validation."""

    @settings(deadline=None)
    @given(st.dictionaries(st.text(max_size=10), st.text(max_size=100), max_size=10))
    def test_small_metadata_always_valid(self, metadata):
        """Small metadata should never raise ValidationError.

        Property: Any small dictionary should never exceed the 64KB limit.
        Max possible size: 10 keys * (10 chars + 100 chars + JSON overhead) < 2KB
        """
        # Act & Assert: Should not raise
        validate_metadata_size(metadata)


class TestMetadataSizeIntegration:
    """Integration tests verifying validation is called in create_task."""

    def test_create_task_validates_metadata_size(self, db_path, repo):
        """create_task() validates metadata size before database insert."""
        # Arrange
        repo.create_epic("test-epic", "Test epic description")

        # Create oversized metadata
        large_metadata = {"data": "x" * 70000}

        # Act & Assert: Should raise ValueError during create_task
        with pytest.raises(ValueError, match="exceeds maximum"):
            repo.create_task(
                epic_name="test-epic",
                title="Test task",
                description="Test description",
                criteria=["Test criterion"],
                metadata=large_metadata,
            )

    def test_create_task_at_limit_succeeds_and_persists(self, db_path, repo):
        """create_task() with metadata at exactly 65536 bytes succeeds and persists.

        P3 fix: Verifies success path for boundary condition.
        """
        from formaltask.tasks.crud import get_tasks

        # Arrange: Create metadata exactly at 65536 bytes
        # JSON overhead: {"data": ""} is 11 bytes, so we need 65536 - 11 = 65525 bytes
        content_size = MAX_METADATA_SIZE - len('{"data": ""}')
        exact_metadata = {"data": "x" * content_size}

        # Verify we're at exactly the limit
        serialized = json.dumps(exact_metadata)
        assert len(serialized.encode("utf-8")) == MAX_METADATA_SIZE

        repo.create_epic("test-epic", "Test epic description")

        # Act: Create task with metadata at limit
        task_id = repo.create_task(
            epic_name="test-epic",
            title="Test task at limit",
            description="Testing boundary condition",
            criteria=["Done"],
            metadata=exact_metadata,
        )

        # Assert: Task created successfully (validation passed, DB insert succeeded)
        assert task_id is not None
        tasks = get_tasks(db_path, "test-epic")
        task_ids = [t["id"] for t in tasks]
        assert task_id in task_ids
