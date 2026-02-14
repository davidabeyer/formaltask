"""Test ReviewPacket schema validation."""

import pytest
from pydantic import ValidationError

from formaltask.review.packet_schema import ReviewPacket
from formaltask.utils.schemas import KNOWN_REVIEW_TYPES


class TestReviewTypesSync:
    @pytest.mark.parametrize("review_type", sorted(KNOWN_REVIEW_TYPES))
    def test_review_packet_accepts_all_known_review_types(self, review_type: str):
        packet = ReviewPacket(
            task_id=42,
            review_type=review_type,
            severity="clean",
            findings=[],
            summary="Test review",
        )
        assert packet.review_type == review_type


class TestFindingLineValidation:
    def _make_packet(self, findings):
        return ReviewPacket(
            task_id=42,
            review_type="code-quality",
            severity="major",
            findings=findings,
            summary="Test",
        )

    def test_finding_line_rejects_string_range(self):
        """String range '382-392' must be rejected — this is the bug."""
        with pytest.raises(ValidationError, match="line"):
            self._make_packet(
                [{"file": "foo.py", "line": "382-392", "priority": "P1", "description": "bug"}]
            )

    def test_finding_line_accepts_none(self):
        """None is valid — guards the `is not None` check for file-level findings."""
        packet = self._make_packet(
            [{"file": "foo.py", "line": None, "priority": "P1", "description": "bug"}]
        )
        assert packet.findings[0]["line"] is None


class TestFindingSeverityNormalization:
    def _make_packet(self, findings):
        return ReviewPacket(
            task_id=42,
            review_type="code-quality",
            severity="major",
            findings=findings,
            summary="Test",
        )

    def test_severity_key_normalized_to_priority(self):
        """Reviewers write 'severity': 'P0' — kernel needs 'priority': 'P0'."""
        packet = self._make_packet(
            [{"file": "a.py", "line": 1, "severity": "P0", "description": "bug"}]
        )
        assert packet.findings[0]["priority"] == "P0"
        assert "severity" not in packet.findings[0]

    def test_priority_key_unchanged(self):
        """Findings already using 'priority' pass through untouched."""
        packet = self._make_packet(
            [{"file": "a.py", "line": 1, "priority": "P1", "description": "bug"}]
        )
        assert packet.findings[0]["priority"] == "P1"

    def test_both_keys_priority_wins(self):
        """If both present, priority kept, severity left alone."""
        packet = self._make_packet(
            [{"file": "a.py", "line": 1, "priority": "P1", "severity": "P0", "description": "bug"}]
        )
        assert packet.findings[0]["priority"] == "P1"
        assert packet.findings[0]["severity"] == "P0"
