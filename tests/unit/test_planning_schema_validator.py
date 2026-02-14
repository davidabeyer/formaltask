"""Tests for planning_schema_validator - validates CriterionV2 in planning YAML files."""


class TestPlanningSchemaValidatorBlocksInvalid:
    """Test that validator blocks invalid CriterionV2 structures."""

    def test_validator_blocks_invalid_criterion_id_pattern(self):
        """Validator should block Write to plan YAML with invalid CriterionV2 id pattern."""
        from formaltask.validators.planning_schema_validator import check

        # CriterionV2 id must match c-{N} or g-{N} pattern
        invalid_yaml_content = """
name: test-epic
description: Test
tasks:
  - title: Test task
    summary: Test summary
    acceptance_criteria:
      - id: invalid-id
        current: Some criterion
"""
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/path/to/foo-plan.yaml",
                "content": invalid_yaml_content,
            },
        }

        result = check(ctx)

        assert result is not None
        assert result["decision"] == "block"
        assert "id" in result["reason"].lower() or "pattern" in result["reason"].lower()


class TestPlanningSchemaValidatorAllowsValid:
    """Test that validator allows valid CriterionV2 structures."""

    def test_validator_allows_valid_criterion_v2(self):
        """Validator should allow Write to plan YAML with valid CriterionV2."""
        from formaltask.validators.planning_schema_validator import check

        # Valid CriterionV2 with c-{N} id pattern and required command field
        valid_yaml_content = """
name: test-epic
description: Test
tasks:
  - title: Test task
    summary: Test summary
    acceptance_criteria:
      - id: c-1
        current: Some criterion
        command: pytest -k test_criterion
"""
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/path/to/foo-plan.yaml",
                "content": valid_yaml_content,
            },
        }

        result = check(ctx)

        assert result is None

    def test_validator_allows_string_criteria(self):
        """Validator should allow plain string acceptance_criteria (non-V2 format)."""
        from formaltask.validators.planning_schema_validator import check

        # Plain string criteria (valid, non-V2 format)
        string_yaml_content = """
name: test-epic
description: Test
tasks:
  - title: Test task
    summary: Test summary
    acceptance_criteria:
      - Tests pass
      - Feature works
"""
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/path/to/foo-spec.yaml",
                "content": string_yaml_content,
            },
        }

        result = check(ctx)

        assert result is None


class TestPlanningSchemaValidatorIgnoresNonYaml:
    """Test that validator ignores non-planning files."""

    def test_validator_ignores_python_files(self):
        """Validator should ignore Write to .py files."""
        from formaltask.validators.planning_schema_validator import check

        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/path/to/foo.py",
                "content": "def main(): pass",
            },
        }

        result = check(ctx)

        assert result is None

    def test_validator_ignores_non_planning_yaml(self):
        """Validator should ignore Write to YAML files that don't match patterns."""
        from formaltask.validators.planning_schema_validator import check

        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/path/to/config.yaml",
                "content": "key: value",
            },
        }

        result = check(ctx)

        assert result is None

    def test_validator_ignores_non_matching_tools(self):
        """Validator should ignore non-Write/Edit/MultiEdit tools."""
        from formaltask.validators.planning_schema_validator import check

        ctx = {
            "tool_name": "Read",
            "tool_input": {
                "file_path": "/path/to/foo-plan.yaml",
            },
        }

        result = check(ctx)

        assert result is None


class TestPlanningSchemaValidatorErrorMessages:
    """Test that validator provides helpful error messages."""

    def test_error_message_includes_field_name(self):
        """Error message should include which field failed validation."""
        from formaltask.validators.planning_schema_validator import check

        invalid_yaml_content = """
tasks:
  - title: Test
    summary: Test
    acceptance_criteria:
      - id: bad
        current: Some text
"""
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/path/to/foo-spec.yaml",
                "content": invalid_yaml_content,
            },
        }

        result = check(ctx)

        assert result is not None
        assert "id" in result["reason"]

    def test_error_message_includes_task_index(self):
        """Error message should include which task has the error."""
        from formaltask.validators.planning_schema_validator import check

        invalid_yaml_content = """
tasks:
  - title: Task 1
    summary: Valid task
    acceptance_criteria:
      - Valid string criterion
  - title: Task 2
    summary: Invalid task
    acceptance_criteria:
      - id: wrong-pattern
        current: Some text
"""
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/path/to/foo-plan.yaml",
                "content": invalid_yaml_content,
            },
        }

        result = check(ctx)

        assert result is not None
        assert "tasks[1]" in result["reason"]

    def test_error_message_includes_validation_detail(self):
        """Error message should explain what's wrong (e.g., pattern requirement)."""
        from formaltask.validators.planning_schema_validator import check

        invalid_yaml_content = """
acceptance_criteria:
  - id: not-valid
    current: Some criterion
"""
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/path/to/task-spec.yaml",
                "content": invalid_yaml_content,
            },
        }

        result = check(ctx)

        assert result is not None
        reason = result["reason"].lower()
        # Should mention pattern requirement
        assert "pattern" in reason or "c-" in reason or "g-" in reason


class TestSchemaVersionValidation:
    """Test schema_version field validation."""

    def test_schema_version_2_raises_validation_error(self):
        """Validator should block YAML with schema_version: 2."""
        from formaltask.validators.planning_schema_validator import check

        yaml_content = """
schema_version: 2
name: test-epic
description: Test
tasks:
  - title: Test task
    summary: Test summary
"""
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/path/to/foo-spec.yaml",
                "content": yaml_content,
            },
        }

        result = check(ctx)

        assert result is not None
        assert result["decision"] == "block"
        assert "schema_version" in result["reason"].lower()
        assert "2" in result["reason"]

    def test_schema_version_1_passes_validation(self):
        """Validator should allow YAML with schema_version: 1."""
        from formaltask.validators.planning_schema_validator import check

        yaml_content = """
schema_version: 1
name: test-epic
description: Test
tasks:
  - title: Test task
    summary: Test summary
"""
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/path/to/foo-spec.yaml",
                "content": yaml_content,
            },
        }

        result = check(ctx)

        assert result is None

    def test_absent_schema_version_defaults_to_1_and_passes(self):
        """Validator should default to schema_version 1 when absent."""
        from formaltask.validators.planning_schema_validator import check

        yaml_content = """
name: test-epic
description: Test
tasks:
  - title: Test task
    summary: Test summary
"""
        ctx = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/path/to/foo-spec.yaml",
                "content": yaml_content,
            },
        }

        result = check(ctx)

        # Should pass - absent schema_version defaults to 1
        assert result is None

    def test_schema_version_default_logic(self):
        """Validator checks schema_version with default=1 when field absent."""
        # This test verifies the implementation uses data.get("schema_version", 1) == 1
        from formaltask.validators.planning_schema_validator import check

        # Test with explicit version 1
        yaml_v1 = """
schema_version: 1
name: test
"""
        ctx_v1 = {
            "tool_name": "Write",
            "tool_input": {"file_path": "/path/to/foo-spec.yaml", "content": yaml_v1},
        }
        assert check(ctx_v1) is None

        # Test with absent version (should default to 1)
        yaml_no_version = """
name: test
"""
        ctx_no_version = {
            "tool_name": "Write",
            "tool_input": {"file_path": "/path/to/foo-spec.yaml", "content": yaml_no_version},
        }
        assert check(ctx_no_version) is None


class TestPlanningSchemaValidatorHookRegistration:
    """Test that validator is registered in pretool hook chain."""

    def test_validator_registered_in_phases(self):
        """planning_schema_validator should be registered in PHASES list."""
        from hooks.pretool.phases import planning_schema_validator
        from hooks.pretool.runner import PHASES

        check_funcs = [fn for fn in PHASES if fn.__module__.endswith("planning_schema_validator")]

        assert len(check_funcs) == 1
        assert check_funcs[0] is planning_schema_validator.check

    def test_validator_exported_from_phases_init(self):
        """planning_schema_validator should be exported from phases __init__."""
        from hooks.pretool import phases

        assert hasattr(phases, "planning_schema_validator")
