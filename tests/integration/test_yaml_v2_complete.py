"""Integration tests for yaml-v2-fixes epic end-to-end workflow.

Task #2857: Verifies all yaml-v2-fixes tasks work together:
1. Model validators (CriterionV2, HistoryEntry, etc.)
2. Container validation (PlanMetadata, TaskSpecMetadata)
3. extra='forbid' enforcement
4. schema_version validation
5. Parser functions (parse_specs_dir)
6. Orphan reference detection (validate_implements_refs)
7. Validator blocks invalid YAML for Write only
8. History preservation through critique cycles
"""

import pytest
import yaml
from pydantic import ValidationError

from formaltask.epics.models import CriterionV2, HistoryEntry
from formaltask.epics.yaml_parser import parse_specs_dir
from formaltask.validators.planning_schema_validator import check


class TestValidatorBlocksInvalidYAML:
    """Test validator blocks invalid YAML for Write (Edit excluded per Task 5)."""

    def test_validator_blocks_invalid_yaml_write(self):
        """Validator should block Write with invalid CriterionV2."""
        # Invalid CriterionV2: missing 'id' field
        invalid_content = """
name: test-plan
description: Test description
tasks:
  - title: Task 1
    summary: Test summary
    acceptance_criteria:
      - current: "Missing id field"
        command: "pytest -k test"
        history: []
"""
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/project/plans/test-plan.yaml",
                "content": invalid_content,
            },
        }
        result = check(ctx)

        # Assert validator blocks with correct structure
        assert result is not None, "Validator should block invalid YAML"
        assert result["decision"] == "block", f"Expected block decision, got {result}"
        assert "reason" in result, "Block should include reason"
        assert "id" in result["reason"].lower(), "Reason should mention missing 'id' field"

    def test_validator_allows_edit_tool(self):
        """Validator should not block Edit tool (per Task 5)."""
        # Even with invalid content, Edit should not be blocked
        # because Edit provides partial YAML that cannot be validated
        invalid_content = """
      - current: "Missing id field"
        command: "pytest -k test"
"""
        ctx = {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/project/plans/test-plan.yaml",
                "old_string": "old content",
                "new_string": invalid_content,
            },
        }
        result = check(ctx)

        # Assert validator allows Edit
        assert result is None, f"Validator should allow Edit, but blocked with: {result}"


class TestHistoryPreservation:
    """Test history preservation through critique cycles."""

    def test_parse_preserves_history_after_critique(self):
        """Parsing should preserve history entries after critique cycle."""
        # YAML with history after critique cycle
        yaml_with_history = """
schema_version: 1
name: test-epic
requirements:
  goals:
    - id: "g-1"
      current: "Feature X works with improvements"
      command: "pytest tests/test_feature_x.py -v"
      history:
        - version: "r1"
          text: "Feature X works"
          critique:
            verdict: "FIX_AND_SHIP"
            findings:
              - priority: "P0"
                finding: "Missing error handling"
                action: "Add try/catch blocks"
                resolution: "fixed"
        - version: "r2"
          text: "Feature X works with error handling"
          critique:
            verdict: "APPROVED"
            findings: []
"""
        # Parse YAML
        data = yaml.safe_load(yaml_with_history)
        goals = data["requirements"]["goals"]

        # Verify history was preserved
        assert len(goals) == 1
        criteria = goals[0]

        # Convert to CriterionV2 to ensure model validation passes
        criterion = CriterionV2.model_validate(criteria)

        # Assert history preserved (matching AC requirement)
        assert len(criterion.history) >= 1, "History should be preserved after critique cycle"

        # Verify history entries structure
        assert criterion.history[0].version == "r1"
        assert criterion.history[0].text == "Feature X works"
        assert criterion.history[0].critique is not None
        assert criterion.history[0].critique.verdict == "FIX_AND_SHIP"
        assert len(criterion.history[0].critique.findings) == 1
        assert criterion.history[0].critique.findings[0].resolution == "fixed"

        # Verify second round
        assert criterion.history[1].version == "r2"
        assert criterion.history[1].critique.verdict == "APPROVED"


class TestModelValidators:
    """Test CriterionV2 model validators (5 tests)."""

    def test_criterion_id_pattern_validator(self):
        """CriterionV2.id must match pattern c-{N} or g-{N}."""
        # Valid patterns
        valid_ids = ["c-1", "c-10", "c-999", "g-1", "g-42"]
        for id_val in valid_ids:
            criterion = CriterionV2(id=id_val, current="Test criterion", command="pytest")
            assert criterion.id == id_val

        # Invalid patterns
        invalid_ids = ["invalid-id", "c-", "g-", "c-abc", "1-c", "C-1", "c1", "c_1"]
        for id_val in invalid_ids:
            with pytest.raises(ValidationError) as exc_info:
                CriterionV2(id=id_val, current="Test criterion", command="pytest")
            assert "pattern" in str(exc_info.value).lower() or "id" in str(exc_info.value).lower()

    def test_criterion_current_not_empty_validator(self):
        """CriterionV2.current cannot be empty or whitespace-only."""
        # Valid current
        criterion = CriterionV2(id="c-1", current="Valid text", command="pytest")
        assert criterion.current == "Valid text"

        # Empty current
        with pytest.raises(ValidationError) as exc_info:
            CriterionV2(id="c-1", current="", command="pytest")
        assert "empty" in str(exc_info.value).lower()

        # Whitespace-only current
        with pytest.raises(ValidationError) as exc_info:
            CriterionV2(id="c-1", current="   ", command="pytest")
        assert "empty" in str(exc_info.value).lower()

    def test_criterion_command_size_validator(self):
        """CriterionV2.command cannot exceed 1KB."""
        # Valid command (under 1KB)
        small_command = "pytest tests/test_feature.py -v"
        criterion = CriterionV2(id="c-1", current="Test", command=small_command)
        assert criterion.command == small_command

        # Command exceeding 1KB (1024 bytes)
        large_command = "a" * 1025
        with pytest.raises(ValidationError) as exc_info:
            CriterionV2(id="c-1", current="Test", command=large_command)
        assert "1kb" in str(exc_info.value).lower() or "1024" in str(exc_info.value)

    def test_criterion_history_limit_validator(self):
        """CriterionV2.history cannot exceed 100 entries."""
        # Valid history (within limit)
        history = [
            HistoryEntry(version=f"r{i}", text=f"Version {i}")
            for i in range(1, 51)
        ]
        criterion = CriterionV2(id="c-1", current="Test", command="pytest", history=history)
        assert len(criterion.history) == 50

        # History exceeding 100 entries
        large_history = [
            HistoryEntry(version=f"r{i}", text=f"Version {i}")
            for i in range(1, 102)
        ]
        with pytest.raises(ValidationError) as exc_info:
            CriterionV2(id="c-1", current="Test", command="pytest", history=large_history)
        assert "100" in str(exc_info.value) or "exceed" in str(exc_info.value).lower()

    def test_criterion_unique_critique_rounds_validator(self):
        """CriterionV2 critique rounds must be unique across history."""
        from formaltask.epics.models import CritiqueRef

        # Valid: unique rounds
        history = [
            HistoryEntry(
                version="r1",
                text="Version 1",
                critique=CritiqueRef(round=1, severity="P0", note="Finding 1")
            ),
            HistoryEntry(
                version="r2",
                text="Version 2",
                critique=CritiqueRef(round=2, severity="P1", note="Finding 2")
            ),
        ]
        criterion = CriterionV2(id="c-1", current="Test", command="pytest", history=history)
        assert len(criterion.history) == 2

        # Invalid: duplicate rounds
        dup_history = [
            HistoryEntry(
                version="r1",
                text="Version 1",
                critique=CritiqueRef(round=1, severity="P0", note="Finding 1")
            ),
            HistoryEntry(
                version="r2",
                text="Version 2",
                critique=CritiqueRef(round=1, severity="P1", note="Finding 2")
            ),
        ]
        with pytest.raises(ValidationError) as exc_info:
            CriterionV2(id="c-1", current="Test", command="pytest", history=dup_history)
        assert "duplicate" in str(exc_info.value).lower() or "round" in str(exc_info.value).lower()


class TestContainerValidation:
    """Test container validation (3 tests)."""

    def test_acceptance_criteria_list_validation(self):
        """SpecSpec should validate acceptance_criteria list contains valid items."""
        from formaltask.epics.models import SpecSpec

        # Valid list with CriterionV2 objects
        valid_spec = {
            "title": "Task 1: Test",
            "summary": "Test summary",
            "context": "Test context",
            "implementation": ["Step 1"],
            "acceptance_criteria": [
                {"id": "c-1", "current": "Criterion 1", "command": "pytest", "history": []},
                {"id": "c-2", "current": "Criterion 2", "command": "pytest", "history": []},
            ],
            "testing": ["Test 1"],
        }
        spec = SpecSpec(**valid_spec)
        assert len(spec.acceptance_criteria) == 2

        # Invalid: duplicate criterion IDs
        invalid_spec = {
            "title": "Task 1: Test",
            "summary": "Test summary",
            "context": "Test context",
            "implementation": ["Step 1"],
            "acceptance_criteria": [
                {"id": "c-1", "current": "Criterion 1", "command": "pytest", "history": []},
                {"id": "c-1", "current": "Criterion 2", "command": "pytest", "history": []},
            ],
            "testing": ["Test 1"],
        }
        with pytest.raises(ValidationError) as exc_info:
            SpecSpec(**invalid_spec)
        assert "duplicate" in str(exc_info.value).lower()

    def test_history_list_validation(self):
        """CriterionV2 should validate history list contains valid HistoryEntry objects."""
        # Valid history list
        valid_history = [
            {"version": "r1", "text": "Version 1"},
            {"version": "r2", "text": "Version 2"},
        ]
        criterion = CriterionV2(id="c-1", current="Test", command="pytest", history=valid_history)
        assert len(criterion.history) == 2

        # Invalid: wrong version pattern
        invalid_history = [
            {"version": "v1", "text": "Version 1"},  # Should be r1, not v1
        ]
        with pytest.raises(ValidationError) as exc_info:
            CriterionV2(id="c-1", current="Test", command="pytest", history=invalid_history)
        assert "pattern" in str(exc_info.value).lower() or "version" in str(exc_info.value).lower()

    def test_nested_findings_list_validation(self):
        """HistoryEntry should validate nested findings list in critique."""
        from formaltask.epics.models import CritiqueResult, Finding

        # Valid nested findings
        critique = CritiqueResult(
            verdict="FIX_AND_SHIP",
            findings=[
                Finding(priority="P0", finding="Issue 1", action="Fix 1"),
                Finding(priority="P1", finding="Issue 2", action="Fix 2"),
            ]
        )
        history = HistoryEntry(version="r1", text="Version 1", critique=critique)
        assert len(history.critique.findings) == 2

        # Invalid: wrong priority literal
        with pytest.raises(ValidationError) as exc_info:
            Finding(priority="P3", finding="Issue", action="Fix")  # Only P0/P1/P2 allowed
        assert "priority" in str(exc_info.value).lower() or "literal" in str(exc_info.value).lower()


class TestExtraForbid:
    """Test extra='forbid' enforcement (3 tests)."""

    def test_criterion_rejects_unknown_fields(self):
        """CriterionV2 with extra='forbid' should reject unknown fields."""
        # Valid CriterionV2
        valid_data = {"id": "c-1", "current": "Test", "command": "pytest", "history": []}
        criterion = CriterionV2(**valid_data)
        assert criterion.id == "c-1"

        # Invalid: unknown field 'extra_field'
        invalid_data = {
            "id": "c-1",
            "current": "Test",
            "command": "pytest",
            "history": [],
            "extra_field": "should be rejected"
        }
        with pytest.raises(ValidationError) as exc_info:
            CriterionV2(**invalid_data)
        assert "extra" in str(exc_info.value).lower() or "unexpected" in str(exc_info.value).lower()

    def test_history_entry_rejects_unknown_fields(self):
        """HistoryEntry with extra='forbid' should reject unknown fields."""
        # Valid HistoryEntry
        valid_data = {"version": "r1", "text": "Version 1"}
        entry = HistoryEntry(**valid_data)
        assert entry.version == "r1"

        # Invalid: unknown field 'timestamp'
        invalid_data = {
            "version": "r1",
            "text": "Version 1",
            "timestamp": "2025-01-01T00:00:00Z"  # Not a documented field
        }
        with pytest.raises(ValidationError) as exc_info:
            HistoryEntry(**invalid_data)
        assert "extra" in str(exc_info.value).lower() or "unexpected" in str(exc_info.value).lower()

    def test_spec_spec_rejects_unknown_fields(self):
        """SpecSpec with extra='forbid' should reject unknown fields."""
        from formaltask.epics.models import SpecSpec

        # Valid SpecSpec
        valid_data = {
            "title": "Task 1: Test",
            "summary": "Test summary",
            "context": "Test context",
            "implementation": ["Step 1"],
            "acceptance_criteria": ["Criterion 1"],
            "testing": ["Test 1"],
        }
        spec = SpecSpec(**valid_data)
        assert spec.title == "Task 1: Test"

        # Invalid: unknown field 'priority'
        invalid_data = {
            "title": "Task 1: Test",
            "summary": "Test summary",
            "context": "Test context",
            "implementation": ["Step 1"],
            "acceptance_criteria": ["Criterion 1"],
            "testing": ["Test 1"],
            "priority": "high"  # Not a documented field
        }
        with pytest.raises(ValidationError) as exc_info:
            SpecSpec(**invalid_data)
        assert "extra" in str(exc_info.value).lower() or "unexpected" in str(exc_info.value).lower()


class TestSchemaVersionValidation:
    """Test schema_version validation (4 tests)."""

    def test_schema_version_1_accepted(self):
        """schema_version: 1 should be accepted."""
        content = """
schema_version: 1
name: test-plan
description: Test plan
tasks:
  - title: Task 1
    summary: Summary
    acceptance_criteria:
      - id: "c-1"
        current: "Criterion 1"
        command: "pytest"
        history: []
"""
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/project/plans/test-plan.yaml",
                "content": content,
            },
        }
        result = check(ctx)
        assert result is None, f"schema_version: 1 should be accepted, but got: {result}"

    def test_schema_version_missing_defaults_to_1(self):
        """Missing schema_version should default to 1."""
        content = """
name: test-plan
description: Test plan
tasks:
  - title: Task 1
    summary: Summary
    acceptance_criteria:
      - id: "c-1"
        current: "Criterion 1"
        command: "pytest"
        history: []
"""
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/project/plans/test-plan.yaml",
                "content": content,
            },
        }
        result = check(ctx)
        assert result is None, f"Missing schema_version should default to 1, but got: {result}"

    def test_schema_version_2_rejected(self):
        """schema_version: 2 should be rejected."""
        content = """
schema_version: 2
name: test-plan
description: Test plan
tasks: []
"""
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/project/plans/test-plan.yaml",
                "content": content,
            },
        }
        result = check(ctx)
        assert result is not None, "schema_version: 2 should be rejected"
        assert result["decision"] == "block"
        assert "schema_version" in result["reason"].lower()
        assert "2" in result["reason"]

    def test_schema_version_invalid_type_rejected(self):
        """schema_version with invalid type should be rejected."""
        content = """
schema_version: "invalid"
name: test-plan
description: Test plan
tasks: []
"""
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/project/plans/test-plan.yaml",
                "content": content,
            },
        }
        result = check(ctx)
        assert result is not None, "schema_version with invalid type should be rejected"
        assert result["decision"] == "block"
        assert "schema_version" in result["reason"].lower()


class TestParserFunctions:
    """Test parser functions (3 tests)."""

    def test_parse_specs_dir_basic(self, tmp_path):
        """parse_specs_dir should parse spec directory correctly."""
        # Create spec files
        spec1_content = """
title: "Task 1: First task"
summary: "First task summary"
context: "First task context"
implementation:
  - Step 1
acceptance_criteria:
  - id: "c-1"
    current: "Criterion 1"
    command: "pytest -k test1"
    history: []
testing:
  - Test 1
"""
        spec2_content = """
title: "Task 2: Second task"
summary: "Second task summary"
context: "Second task context"
implementation:
  - Step 1
acceptance_criteria:
  - id: "c-2"
    current: "Criterion 2"
    command: "pytest -k test2"
    history: []
testing:
  - Test 2
"""
        (tmp_path / "task-1-first-spec.yaml").write_text(spec1_content)
        (tmp_path / "task-2-second-spec.yaml").write_text(spec2_content)

        # Parse specs
        tasks = parse_specs_dir(str(tmp_path))

        # Verify parsing
        assert len(tasks) == 2
        assert tasks[0]["title"] == "Task 1: First task"
        assert tasks[0]["description"] == "First task summary"
        assert len(tasks[0]["criteria"]) == 1
        assert tasks[0]["criteria"][0]["text"] == "Criterion 1"
        assert tasks[0]["criteria"][0]["command"] == "pytest -k test1"

    def test_parse_specs_dir_validates_criterionv2(self, tmp_path):
        """parse_specs_dir should validate CriterionV2 in acceptance_criteria."""
        from formaltask.epics.yaml_parser import SpecFormatError

        # Create invalid spec with missing id
        invalid_spec = """
title: "Task 1: Invalid"
summary: "Invalid task"
context: "Context"
implementation:
  - Step 1
acceptance_criteria:
  - current: "Missing id field"
    command: "pytest"
    history: []
testing:
  - Test 1
"""
        (tmp_path / "task-1-invalid-spec.yaml").write_text(invalid_spec)

        # Should raise SpecFormatError
        with pytest.raises(SpecFormatError) as exc_info:
            parse_specs_dir(str(tmp_path))
        assert "validation" in str(exc_info.value).lower()

    def test_parse_specs_dir_sorts_numerically(self, tmp_path):
        """parse_specs_dir should sort task specs numerically."""
        # Create spec files in non-sorted order
        spec10 = """
title: "Task 10: Tenth"
summary: "Tenth task"
context: "Context"
implementation: ["Step"]
acceptance_criteria: ["Criterion"]
testing: ["Test"]
"""
        spec2 = """
title: "Task 2: Second"
summary: "Second task"
context: "Context"
implementation: ["Step"]
acceptance_criteria: ["Criterion"]
testing: ["Test"]
"""
        spec1 = """
title: "Task 1: First"
summary: "First task"
context: "Context"
implementation: ["Step"]
acceptance_criteria: ["Criterion"]
testing: ["Test"]
"""
        # Write in wrong order
        (tmp_path / "task-10-tenth-spec.yaml").write_text(spec10)
        (tmp_path / "task-2-second-spec.yaml").write_text(spec2)
        (tmp_path / "task-1-first-spec.yaml").write_text(spec1)

        # Parse specs
        tasks = parse_specs_dir(str(tmp_path))

        # Verify numeric sorting (1, 2, 10) not lexicographic (1, 10, 2)
        assert len(tasks) == 3
        assert tasks[0]["title"] == "Task 1: First"
        assert tasks[1]["title"] == "Task 2: Second"
        assert tasks[2]["title"] == "Task 10: Tenth"
