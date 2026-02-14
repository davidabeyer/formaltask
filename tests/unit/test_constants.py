"""Tests for FormalTask constants module.

Verifies StrEnum types for status values maintain backward compatibility
with existing string comparisons in the codebase.
"""

from tests.fixtures.paths import SCHEMA_FILE


class TestStatusCheckConstraint:
    """Test database CHECK constraint for task status."""

    def test_production_schema_has_status_check_constraint(self):
        """Production schema should include CHECK constraint on status."""
        schema_content = SCHEMA_FILE.read_text()

        # Verify CHECK constraint exists for status column (includes all valid statuses)
        assert (
            "CHECK(status IN ('open', 'in_progress', 'completed', 'cancelled', 'deferred', 'pending_merge', 'blocked', 'pending_review', 'blocked_user'))"
            in schema_content
        )
