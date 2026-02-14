"""Integration tests for UTF-8 byte counting in create_task() size validation.

Tests that create_task() correctly validates description size using UTF-8 byte
counting (not character counting). This is critical for internationalization
where a single character can be multiple bytes:
- ASCII: 1 byte per character
- Emoji (e.g., "🎉"): 4 bytes per character
- CJK characters: 3 bytes per character

The description limit is 64KB (65536 bytes). With emojis at 4 bytes each:
- 16384 emojis = exactly 64KB (65536 bytes) - should pass
- 16385 emojis = 65540 bytes > 64KB - should fail

Task #1093: P1 - Critical internationalization boundary test
"""

import pytest


class TestCreateTaskUtf8ByteCounting:
    """Integration tests for UTF-8 byte counting in create_task()."""

    @pytest.fixture
    def repo_with_epic(self, repo):
        """Repository with a test epic already created."""
        repo.create_epic("test-epic", "Test epic for UTF-8 byte counting tests")
        return repo

    def test_create_task_description_at_64kb_boundary_with_emojis_passes(self, repo_with_epic):
        """16384 emojis (exactly 64KB) should pass size validation.

        Each emoji "🎉" is 4 UTF-8 bytes.
        16384 * 4 = 65536 bytes = exactly 64KB limit.
        """
        # Arrange: Create description with exactly 16384 emojis (64KB)
        emoji = "🎉"  # 4 bytes in UTF-8
        emoji_count = 16384  # 16384 * 4 = 65536 bytes = 64KB exactly
        description = emoji * emoji_count

        # Verify our math: exactly 64KB
        assert len(description.encode("utf-8")) == 65536

        # Act: Create task with exactly 64KB description
        task_id = repo_with_epic.create_task(
            epic_name="test-epic",
            title="UTF-8 boundary test task",
            description=description,
            criteria=["Test criterion"],
        )

        # Assert: Task was created successfully
        assert task_id is not None
        assert task_id > 0

    def test_create_task_description_exceeds_64kb_boundary_with_emojis_fails(self, repo_with_epic):
        """16385 emojis (65540 bytes) should fail size validation.

        Each emoji "🎉" is 4 UTF-8 bytes.
        16385 * 4 = 65540 bytes > 64KB limit (65536 bytes).
        """
        # Arrange: Create description with 16385 emojis (exceeds 64KB)
        emoji = "🎉"  # 4 bytes in UTF-8
        emoji_count = 16385  # 16385 * 4 = 65540 bytes > 64KB
        description = emoji * emoji_count

        # Verify our math: exceeds 64KB by 4 bytes
        assert len(description.encode("utf-8")) == 65540

        # Act & Assert: Should raise ValueError for exceeding size limit
        with pytest.raises(ValueError) as exc_info:
            repo_with_epic.create_task(
                epic_name="test-epic",
                title="UTF-8 boundary test task",
                description=description,
                criteria=["Test criterion"],
            )

        # Verify error message mentions bytes (not characters)
        assert "65536" in str(exc_info.value) or "bytes" in str(exc_info.value).lower()
