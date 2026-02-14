"""Tests for Pydantic models in formaltask.epics.models."""

import pytest
from pydantic import ValidationError

from formaltask.epics.models import (
    CriterionV2,
    CritiqueRef,
    CritiqueResult,
    Finding,
    HistoryEntry,
    SpecSpec,
)


class TestCriterionV2:
    """Tests for CriterionV2 model."""

    def test_criterion_v2_valid_structure_c_pattern(self):
        """CriterionV2 validates with c-N pattern id."""
        result = CriterionV2.model_validate(
            {"id": "c-1", "current": "text", "command": "pytest -k test", "history": []}
        )
        assert result.id == "c-1"
        assert result.current == "text"
        assert result.command == "pytest -k test"
        assert result.history == []

    def test_criterion_v2_valid_structure_g_pattern(self):
        """CriterionV2 validates with g-N pattern id."""
        result = CriterionV2.model_validate(
            {"id": "g-42", "current": "goal text", "command": "pytest -k goal", "history": []}
        )
        assert result.id == "g-42"
        assert result.current == "goal text"
        assert result.command == "pytest -k goal"

    def test_criterion_v2_invalid_id_pattern(self):
        """CriterionV2 raises ValidationError for invalid id pattern."""
        with pytest.raises(ValidationError) as exc_info:
            CriterionV2.model_validate({"id": "invalid", "current": "text", "history": []})
        assert "id must match pattern" in str(exc_info.value).lower()

    def test_criterion_v2_invalid_id_pattern_wrong_prefix(self):
        """CriterionV2 rejects id with wrong prefix."""
        with pytest.raises(ValidationError):
            CriterionV2.model_validate({"id": "x-1", "current": "text", "history": []})

    def test_criterion_v2_empty_current_raises(self):
        """CriterionV2 with empty current raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CriterionV2.model_validate({"id": "c-1", "current": "", "history": []})
        assert "current cannot be empty" in str(exc_info.value).lower()

    def test_criterion_v2_whitespace_only_current_raises(self):
        """CriterionV2 with whitespace-only current raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CriterionV2.model_validate({"id": "c-1", "current": "   ", "history": []})
        assert "current cannot be empty" in str(exc_info.value).lower()

    def test_criterion_v2_duplicate_critique_round_raises(self):
        """CriterionV2 with duplicate critique.round in history raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CriterionV2.model_validate(
                {
                    "id": "c-1",
                    "current": "text",
                    "command": "pytest -k test",
                    "history": [
                        {
                            "version": "r1",
                            "text": "v1",
                            "critique": {"round": 1, "severity": "P0", "note": "issue1"},
                        },
                        {
                            "version": "r2",
                            "text": "v2",
                            "critique": {"round": 1, "severity": "P1", "note": "issue2"},
                        },
                    ],
                }
            )
        assert "duplicate critique round" in str(exc_info.value).lower()

    def test_criterion_v2_unique_critique_rounds_valid(self):
        """CriterionV2 with unique critique.round values is valid."""
        result = CriterionV2.model_validate(
            {
                "id": "c-1",
                "current": "text",
                "command": "pytest -k test",
                "history": [
                    {
                        "version": "r1",
                        "text": "v1",
                        "critique": {"round": 1, "severity": "P0", "note": "issue1"},
                    },
                    {
                        "version": "r2",
                        "text": "v2",
                        "critique": {"round": 2, "severity": "P1", "note": "issue2"},
                    },
                ],
            }
        )
        assert len(result.history) == 2

    def test_criterion_v2_history_limit_exceeded_raises(self):
        """CriterionV2 with >100 history entries raises ValidationError."""
        history = [{"version": f"r{i}", "text": f"v{i}"} for i in range(1, 102)]
        with pytest.raises(ValidationError) as exc_info:
            CriterionV2.model_validate({"id": "c-1", "current": "text", "history": history})
        assert "history cannot exceed 100 entries" in str(exc_info.value).lower()

    def test_criterion_v2_history_at_limit_valid(self):
        """CriterionV2 with exactly 100 history entries is valid."""
        history = [{"version": f"r{i}", "text": f"v{i}"} for i in range(1, 101)]
        result = CriterionV2.model_validate(
            {"id": "c-1", "current": "text", "command": "pytest -k test", "history": history}
        )
        assert len(result.history) == 100

    def test_criterion_v2_with_command_field(self):
        """CriterionV2.model_validate({'id': 'c-1', 'current': 'test', 'command': 'pytest -k test', 'history': []}) succeeds."""
        result = CriterionV2.model_validate(
            {"id": "c-1", "current": "test", "command": "pytest -k test", "history": []}
        )
        assert result.id == "c-1"
        assert result.current == "test"
        assert result.command == "pytest -k test"
        assert result.history == []

    def test_criterion_v2_command_field_optional(self):
        """CriterionV2 without command field succeeds with None default."""
        result = CriterionV2.model_validate(
            {"id": "c-1", "current": "test", "history": []}
        )
        assert result.id == "c-1"
        assert result.current == "test"
        assert result.command is None
        assert result.history == []


class TestHistoryEntry:
    """Tests for HistoryEntry model."""

    def test_history_entry_minimal(self):
        """HistoryEntry validates with minimal required fields."""
        result = HistoryEntry.model_validate({"version": "r1", "text": "original text"})
        assert result.version == "r1"
        assert result.text == "original text"
        assert result.critique is None

    def test_history_entry_with_critique_result(self):
        """HistoryEntry validates with CritiqueResult."""
        result = HistoryEntry.model_validate(
            {
                "version": "r1",
                "text": "t",
                "critique": {
                    "verdict": "FIX_AND_SHIP",
                    "findings": [
                        {
                            "priority": "P0",
                            "finding": "critical issue",
                            "action": "fix it",
                            "resolution": "fixed",
                        }
                    ],
                },
            }
        )
        assert result.critique is not None
        assert result.critique.verdict == "FIX_AND_SHIP"
        assert len(result.critique.findings) == 1
        assert result.critique.findings[0].priority == "P0"
        assert result.critique.findings[0].finding == "critical issue"
        assert result.critique.findings[0].action == "fix it"
        assert result.critique.findings[0].resolution == "fixed"

    def test_history_entry_with_resolution(self):
        """HistoryEntry validates with resolution when critique is present."""
        result = HistoryEntry.model_validate(
            {
                "version": "r2",
                "text": "updated text",
                "critique": {"round": 1, "severity": "P0", "note": "issue"},
                "resolution": "fixed",
            }
        )
        assert result.resolution == "fixed"

    def test_history_entry_invalid_resolution(self):
        """HistoryEntry raises ValidationError for invalid resolution literal."""
        with pytest.raises(ValidationError):
            HistoryEntry.model_validate({"version": "r1", "text": "t", "resolution": "invalid"})

    def test_history_entry_valid_resolutions(self):
        """HistoryEntry accepts all valid resolution values when critique is present."""
        for resolution in ["fixed", "wontfix", "deferred"]:
            result = HistoryEntry.model_validate(
                {
                    "version": "r1",
                    "text": "t",
                    "critique": {"round": 1, "severity": "P1", "note": "issue"},
                    "resolution": resolution,
                }
            )
            assert result.resolution == resolution

    def test_history_entry_with_approved_critique(self):
        """HistoryEntry validates with APPROVED verdict and no findings."""
        result = HistoryEntry.model_validate(
            {
                "version": "r1",
                "text": "t",
                "critique": {"verdict": "APPROVED", "findings": []},
            }
        )
        assert result.critique is not None
        assert result.critique.verdict == "APPROVED"
        assert result.critique.findings == []

    def test_history_entry_resolution_without_critique_raises(self):
        """HistoryEntry with resolution but no critique raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            HistoryEntry.model_validate({"version": "r1", "text": "t", "resolution": "fixed"})
        assert "resolution requires critique" in str(exc_info.value).lower()

    def test_history_entry_version_valid_r_pattern(self):
        """HistoryEntry accepts valid r{N} version formats."""
        for version in ["r1", "r2", "r10", "r100"]:
            result = HistoryEntry.model_validate({"version": version, "text": "t"})
            assert result.version == version

    def test_history_entry_version_rejects_v1(self):
        """HistoryEntry rejects v1 version format."""
        with pytest.raises(ValidationError) as exc_info:
            HistoryEntry.model_validate({"version": "v1", "text": "t"})
        assert "version must match pattern r{n}" in str(exc_info.value).lower()

    def test_history_entry_version_rejects_round_1(self):
        """HistoryEntry rejects round-1 version format."""
        with pytest.raises(ValidationError) as exc_info:
            HistoryEntry.model_validate({"version": "round-1", "text": "t"})
        assert "version must match pattern r{n}" in str(exc_info.value).lower()

    def test_history_entry_version_rejects_r1a(self):
        """HistoryEntry rejects r1a version format."""
        with pytest.raises(ValidationError) as exc_info:
            HistoryEntry.model_validate({"version": "r1a", "text": "t"})
        assert "version must match pattern r{n}" in str(exc_info.value).lower()


class TestCritiqueRef:
    """Tests for CritiqueRef model (legacy format)."""

    def test_critique_ref_valid(self):
        """CritiqueRef validates with valid structure."""
        result = CritiqueRef.model_validate(
            {"round": 1, "severity": "P0", "note": "critical issue"}
        )
        assert result.round == 1
        assert result.severity == "P0"
        assert result.note == "critical issue"

    def test_critique_ref_all_severities(self):
        """CritiqueRef accepts all valid severity values."""
        for severity in ["P0", "P1", "P2"]:
            result = CritiqueRef.model_validate({"round": 1, "severity": severity, "note": "issue"})
            assert result.severity == severity

    def test_critique_ref_invalid_severity(self):
        """CritiqueRef rejects invalid severity."""
        with pytest.raises(ValidationError):
            CritiqueRef.model_validate({"round": 1, "severity": "P3", "note": "issue"})


class TestFinding:
    """Tests for Finding model."""

    def test_finding_valid(self):
        """Finding validates with valid structure."""
        result = Finding.model_validate(
            {"priority": "P1", "finding": "Missing validation", "action": "Add input validation"}
        )
        assert result.priority == "P1"
        assert result.finding == "Missing validation"
        assert result.action == "Add input validation"
        assert result.resolution is None

    def test_finding_with_resolution(self):
        """Finding validates with resolution."""
        result = Finding.model_validate(
            {
                "priority": "P0",
                "finding": "Security issue",
                "action": "Fix ASAP",
                "resolution": "fixed",
            }
        )
        assert result.resolution == "fixed"

    def test_finding_all_priorities(self):
        """Finding accepts all valid priority values."""
        for priority in ["P0", "P1", "P2"]:
            result = Finding.model_validate(
                {"priority": priority, "finding": "issue", "action": "act"}
            )
            assert result.priority == priority

    def test_finding_invalid_priority(self):
        """Finding rejects invalid priority."""
        with pytest.raises(ValidationError):
            Finding.model_validate({"priority": "P3", "finding": "issue", "action": "act"})

    def test_finding_all_resolutions(self):
        """Finding accepts all valid resolution values."""
        for resolution in ["fixed", "rejected", "deferred"]:
            result = Finding.model_validate(
                {"priority": "P1", "finding": "issue", "action": "act", "resolution": resolution}
            )
            assert result.resolution == resolution

    def test_finding_invalid_resolution(self):
        """Finding rejects invalid resolution."""
        with pytest.raises(ValidationError):
            Finding.model_validate(
                {"priority": "P1", "finding": "issue", "action": "act", "resolution": "invalid"}
            )


class TestCritiqueResult:
    """Tests for CritiqueResult model."""

    def test_critique_result_with_findings(self):
        """CritiqueResult validates with findings."""
        result = CritiqueResult.model_validate(
            {
                "verdict": "FIX_AND_SHIP",
                "findings": [
                    {"priority": "P1", "finding": "issue", "action": "fix"},
                    {"priority": "P2", "finding": "minor", "action": "consider"},
                ],
            }
        )
        assert result.verdict == "FIX_AND_SHIP"
        assert len(result.findings) == 2
        assert result.findings[0].priority == "P1"
        assert result.findings[1].priority == "P2"

    def test_critique_result_approved_empty_findings(self):
        """CritiqueResult validates APPROVED with no findings."""
        result = CritiqueResult.model_validate({"verdict": "APPROVED", "findings": []})
        assert result.verdict == "APPROVED"
        assert result.findings == []

    def test_critique_result_approved_defaults_empty_findings(self):
        """CritiqueResult defaults findings to empty list."""
        result = CritiqueResult.model_validate({"verdict": "APPROVED"})
        assert result.findings == []

    def test_critique_result_all_verdicts(self):
        """CritiqueResult accepts all valid verdict values."""
        for verdict in ["APPROVED", "FIX_AND_SHIP", "REVISE"]:
            result = CritiqueResult.model_validate({"verdict": verdict})
            assert result.verdict == verdict

    def test_critique_result_invalid_verdict(self):
        """CritiqueResult rejects invalid verdict."""
        with pytest.raises(ValidationError):
            CritiqueResult.model_validate({"verdict": "INVALID"})


class TestFindingEdgeCases:
    """Edge case tests for Finding model."""

    def test_finding_special_characters(self):
        """Finding handles special characters in text fields."""
        result = Finding.model_validate(
            {
                "priority": "P1",
                "finding": "Issue with `code` and \"quotes\" and 'apostrophes'",
                "action": "Fix <html> & entities",
            }
        )
        assert "`code`" in result.finding
        assert "<html>" in result.action

    def test_finding_unicode_text(self):
        """Finding handles unicode characters."""
        result = Finding.model_validate(
            {
                "priority": "P0",
                "finding": "Error in 日本語 module: émojis 🎉",
                "action": "Fix unicode handling: café résumé",
            }
        )
        assert "日本語" in result.finding
        assert "🎉" in result.finding
        assert "café" in result.action

    def test_finding_multiline_text(self):
        """Finding handles multiline text."""
        result = Finding.model_validate(
            {
                "priority": "P1",
                "finding": "Line 1\nLine 2\nLine 3",
                "action": "Step 1: Do X\nStep 2: Do Y",
            }
        )
        assert "\n" in result.finding
        assert "Line 2" in result.finding

    def test_finding_long_text(self):
        """Finding handles long text strings."""
        long_text = "A" * 5000
        result = Finding.model_validate(
            {"priority": "P2", "finding": long_text, "action": "Simplify"}
        )
        assert len(result.finding) == 5000

    def test_finding_empty_string_allowed(self):
        """Finding allows empty strings (Pydantic default behavior)."""
        result = Finding.model_validate(
            {"priority": "P1", "finding": "", "action": ""}
        )
        assert result.finding == ""
        assert result.action == ""


class TestCritiqueResultEdgeCases:
    """Edge case tests for CritiqueResult model."""

    def test_critique_result_many_findings(self):
        """CritiqueResult handles many findings."""
        findings = [
            {"priority": f"P{i % 3}", "finding": f"Issue {i}", "action": f"Fix {i}"}
            for i in range(100)
        ]
        result = CritiqueResult.model_validate(
            {"verdict": "REVISE", "findings": findings}
        )
        assert len(result.findings) == 100

    def test_critique_result_mixed_resolutions(self):
        """CritiqueResult handles findings with mixed resolutions."""
        result = CritiqueResult.model_validate(
            {
                "verdict": "FIX_AND_SHIP",
                "findings": [
                    {"priority": "P0", "finding": "A", "action": "Fix", "resolution": "fixed"},
                    {"priority": "P1", "finding": "B", "action": "Skip", "resolution": "rejected"},
                    {"priority": "P2", "finding": "C", "action": "Later", "resolution": "deferred"},
                    {"priority": "P1", "finding": "D", "action": "Pending"},  # No resolution
                ],
            }
        )
        assert result.findings[0].resolution == "fixed"
        assert result.findings[1].resolution == "rejected"
        assert result.findings[2].resolution == "deferred"
        assert result.findings[3].resolution is None

    def test_critique_result_approved_with_findings_allowed(self):
        """APPROVED verdict can still have findings (e.g., informational)."""
        result = CritiqueResult.model_validate(
            {
                "verdict": "APPROVED",
                "findings": [
                    {"priority": "P2", "finding": "Minor suggestion", "action": "Consider later"}
                ],
            }
        )
        assert result.verdict == "APPROVED"
        assert len(result.findings) == 1


class TestHistoryEntryEdgeCases:
    """Edge case tests for HistoryEntry model."""

    def test_history_entry_multiple_findings(self):
        """HistoryEntry can have critique with multiple findings."""
        result = HistoryEntry.model_validate(
            {
                "version": "r3",
                "text": "Updated criterion",
                "critique": {
                    "verdict": "REVISE",
                    "findings": [
                        {"priority": "P0", "finding": "Critical 1", "action": "Fix now"},
                        {"priority": "P0", "finding": "Critical 2", "action": "Also fix"},
                        {"priority": "P1", "finding": "Important", "action": "Address soon"},
                    ],
                },
            }
        )
        assert result.critique is not None
        assert len(result.critique.findings) == 3

    def test_history_entry_empty_version_rejected(self):
        """HistoryEntry rejects empty version string."""
        with pytest.raises(ValidationError) as exc_info:
            HistoryEntry.model_validate({"version": "", "text": "text"})
        assert "version must match pattern r{n}" in str(exc_info.value).lower()






class TestSpecSpecAcceptanceCriteria:
    """Tests for SpecSpec acceptance_criteria with CriterionV2."""

    def test_spec_spec_accepts_criterion_v2(self):
        """SpecSpec validates with CriterionV2 format acceptance_criteria."""
        result = SpecSpec.model_validate(
            {
                "title": "Task 1: Test Task",
                "summary": "Test summary",
                "context": "Test context",
                "implementation": ["step 1"],
                "acceptance_criteria": [{"id": "c-1", "current": "text", "command": "pytest -k test", "history": []}],
                "testing": ["test 1"],
            }
        )
        assert len(result.acceptance_criteria) == 1
        assert isinstance(result.acceptance_criteria[0], CriterionV2)

    def test_spec_spec_accepts_legacy_strings(self):
        """SpecSpec validates with legacy string format."""
        result = SpecSpec.model_validate(
            {
                "title": "Task 1: Test Task",
                "summary": "Test summary",
                "context": "Test context",
                "implementation": ["step 1"],
                "acceptance_criteria": ["plain string criterion"],
                "testing": ["test 1"],
            }
        )
        assert len(result.acceptance_criteria) == 1
        assert result.acceptance_criteria[0] == "plain string criterion"




class TestSpecSpecTitleField:
    """Tests for SpecSpec title field (required)."""

    def test_specspec_title_required(self):
        """SpecSpec without title field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SpecSpec.model_validate(
                {
                    "summary": "Test summary",
                    "context": "Test context",
                    "implementation": ["step 1"],
                    "acceptance_criteria": [
                        {"id": "c-1", "current": "criterion", "command": "pytest -k test", "history": []}
                    ],
                    "testing": ["test 1"],
                }
            )
        assert "title" in str(exc_info.value).lower()

    def test_specspec_with_title_valid(self):
        """SpecSpec with title field is valid."""
        result = SpecSpec.model_validate(
            {
                "title": "Task 1: Core Parser",
                "summary": "Test summary",
                "context": "Test context",
                "implementation": ["step 1"],
                "acceptance_criteria": [
                    {"id": "c-1", "current": "criterion", "command": "pytest -k test", "history": []}
                ],
                "testing": ["test 1"],
            }
        )
        assert result.title == "Task 1: Core Parser"


class TestSpecSpecDuplicateCriterionIds:
    """Tests for SpecSpec duplicate criterion ID validation."""

    def test_spec_spec_duplicate_criterion_ids_raises(self):
        """SpecSpec with duplicate criterion IDs raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SpecSpec.model_validate(
                {
                    "title": "Task 1: Test Task",
                    "summary": "Test summary",
                    "context": "Test context",
                    "implementation": ["step 1"],
                    "acceptance_criteria": [
                        {"id": "c-1", "current": "first criterion", "command": "pytest -k c1", "history": []},
                        {"id": "c-1", "current": "duplicate id", "command": "pytest -k dup", "history": []},
                    ],
                    "testing": ["test 1"],
                }
            )
        assert "duplicate criterion ids found" in str(exc_info.value).lower()

    def test_spec_spec_unique_criterion_ids_valid(self):
        """SpecSpec with unique criterion IDs is valid."""
        result = SpecSpec.model_validate(
            {
                "title": "Task 1: Test Task",
                "summary": "Test summary",
                "context": "Test context",
                "implementation": ["step 1"],
                "acceptance_criteria": [
                    {"id": "c-1", "current": "first criterion", "command": "pytest -k c1", "history": []},
                    {"id": "c-2", "current": "second criterion", "command": "pytest -k c2", "history": []},
                ],
                "testing": ["test 1"],
            }
        )
        assert len(result.acceptance_criteria) == 2


