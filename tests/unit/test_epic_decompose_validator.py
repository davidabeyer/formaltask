"""Unit tests for epic_decompose_validator.py.

Tests spec directory validation for ft epic decompose command.
"""

from hooks.pretool.phases import epic_decompose_validator


# Valid spec YAML content for testing
VALID_SPEC_YAML = """
title: "Task 1: Test Task"
summary: Test task summary
context: Test context for the task
implementation:
  - Step 1
  - Step 2
acceptance_criteria:
  - id: c-1
    current: Criterion 1
    command: "echo 'test'"
testing:
  - Test 1
"""

# Invalid spec YAML - missing required title field
INVALID_SPEC_MISSING_TITLE = """
summary: Test task summary
context: Test context for the task
implementation:
  - Step 1
acceptance_criteria:
  - Criterion 1
testing:
  - Test 1
"""


class TestCheckCommand:
    """Tests for check() function command matching."""

    def test_check_ignores_non_bash_tools(self):
        """check() returns None for non-Bash tools."""
        ctx = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/path"},
        }
        result = epic_decompose_validator.check(ctx)
        assert result is None

    def test_check_ignores_non_epic_decompose_commands(self):
        """check() returns None for non-epic-decompose commands."""
        ctx = {
            "tool_name": "Bash",
            "tool_input": {"command": "ft task-list my-epic"},
        }
        result = epic_decompose_validator.check(ctx)
        assert result is None

    def test_check_matches_simple_command(self, tmp_path):
        """check() matches basic ft epic decompose command."""
        # Create valid spec directory
        spec_dir = tmp_path / "specs"
        spec_dir.mkdir()
        (spec_dir / "task-1-test-spec.yaml").write_text(VALID_SPEC_YAML)

        ctx = {
            "tool_name": "Bash",
            "tool_input": {"command": f"ft epic decompose my-epic {spec_dir}"},
        }
        result = epic_decompose_validator.check(ctx)
        assert result is None  # Valid, no blocking

    def test_check_matches_piped_command(self, tmp_path):
        """check() matches ft epic decompose in piped command."""
        # Create valid spec directory
        spec_dir = tmp_path / "specs"
        spec_dir.mkdir()
        (spec_dir / "task-1-test-spec.yaml").write_text(VALID_SPEC_YAML)

        ctx = {
            "tool_name": "Bash",
            "tool_input": {"command": f"echo 'before' && ft epic decompose my-epic {spec_dir}"},
        }
        result = epic_decompose_validator.check(ctx)
        assert result is None  # Valid, no blocking


class TestCheckSpecDirectory:
    """Tests for check() function spec directory validation."""

    def test_check_blocks_missing_directory(self, tmp_path):
        """check() blocks when spec directory doesn't exist."""
        nonexistent = tmp_path / "nonexistent-specs"

        ctx = {
            "tool_name": "Bash",
            "tool_input": {"command": f"ft epic decompose my-epic {nonexistent}"},
        }
        result = epic_decompose_validator.check(ctx)

        assert result is not None
        assert result["decision"] == "block"
        assert "not found" in result["reason"].lower()

    def test_check_blocks_file_instead_of_directory(self, tmp_path):
        """check() blocks when path is a file, not a directory."""
        file_path = tmp_path / "not-a-dir.txt"
        file_path.write_text("I'm a file")

        ctx = {
            "tool_name": "Bash",
            "tool_input": {"command": f"ft epic decompose my-epic {file_path}"},
        }
        result = epic_decompose_validator.check(ctx)

        assert result is not None
        assert result["decision"] == "block"
        assert "directory" in result["reason"].lower()

    def test_check_blocks_empty_directory(self, tmp_path):
        """check() blocks when spec directory has no spec files."""
        spec_dir = tmp_path / "empty-specs"
        spec_dir.mkdir()

        ctx = {
            "tool_name": "Bash",
            "tool_input": {"command": f"ft epic decompose my-epic {spec_dir}"},
        }
        result = epic_decompose_validator.check(ctx)

        assert result is not None
        assert result["decision"] == "block"
        assert "no spec files" in result["reason"].lower()

    def test_check_blocks_invalid_spec_content(self, tmp_path):
        """check() blocks when spec file has invalid content."""
        spec_dir = tmp_path / "bad-specs"
        spec_dir.mkdir()
        # Missing required 'title' field
        (spec_dir / "task-1-test-spec.yaml").write_text(INVALID_SPEC_MISSING_TITLE)

        ctx = {
            "tool_name": "Bash",
            "tool_input": {"command": f"ft epic decompose my-epic {spec_dir}"},
        }
        result = epic_decompose_validator.check(ctx)

        assert result is not None
        assert result["decision"] == "block"
        # Should mention validation error
        assert "title" in result["reason"].lower() or "validation" in result["reason"].lower()

    def test_check_allows_valid_spec_directory(self, tmp_path):
        """check() allows valid spec directory."""
        spec_dir = tmp_path / "valid-specs"
        spec_dir.mkdir()
        (spec_dir / "task-1-parser-spec.yaml").write_text(VALID_SPEC_YAML)

        ctx = {
            "tool_name": "Bash",
            "tool_input": {"command": f"ft epic decompose my-epic {spec_dir}"},
        }
        result = epic_decompose_validator.check(ctx)

        assert result is None  # No blocking


class TestValidateSpecDir:
    """Tests for validate_spec_dir() function directly."""

    def test_validate_spec_dir_returns_none_for_valid(self, tmp_path):
        """validate_spec_dir() returns None for valid spec directory."""
        spec_dir = tmp_path / "specs"
        spec_dir.mkdir()
        (spec_dir / "task-1-test-spec.yaml").write_text(VALID_SPEC_YAML)

        result = epic_decompose_validator.validate_spec_dir(spec_dir)
        assert result is None

    def test_validate_spec_dir_returns_error_for_invalid(self, tmp_path):
        """validate_spec_dir() returns error message for invalid specs."""
        spec_dir = tmp_path / "specs"
        spec_dir.mkdir()
        (spec_dir / "task-1-test-spec.yaml").write_text(INVALID_SPEC_MISSING_TITLE)

        result = epic_decompose_validator.validate_spec_dir(spec_dir)
        assert result is not None
        assert "title" in result.lower() or "validation" in result.lower()
