"""Tests for hook input analysis script.

TDD Red Phase: These tests define the expected behavior of the
analyze-hook-input.py script which analyzes captured Claude Code
hook input to determine the PreToolUseHookData schema.
"""

import json
from pathlib import Path

import pytest


class TestAnalyzeScriptParsesValidJsonl:
    """Test that the analysis script correctly parses valid JSONL files."""

    def test_parses_single_line_jsonl(self, tmp_path: Path):
        """Script correctly parses single-line JSONL file."""
        from hooks.scripts.analyze_hook_input import parse_jsonl_samples

        jsonl_file = tmp_path / "samples.jsonl"
        sample = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
        jsonl_file.write_text(json.dumps(sample) + "\n")

        samples = parse_jsonl_samples(jsonl_file)

        assert len(samples) == 1
        assert samples[0]["tool_name"] == "Bash"
        assert samples[0]["tool_input"]["command"] == "ls"

    def test_parses_multi_line_jsonl(self, tmp_path: Path):
        """Script correctly parses multi-line JSONL file."""
        from hooks.scripts.analyze_hook_input import parse_jsonl_samples

        jsonl_file = tmp_path / "samples.jsonl"
        samples_data = [
            {"tool_name": "Bash", "tool_input": {"command": "ls"}},
            {"tool_name": "Read", "tool_input": {"file_path": "/tmp/test.py"}},
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "/tmp/test.py", "old_string": "a", "new_string": "b"},
            },
        ]
        jsonl_file.write_text("\n".join(json.dumps(s) for s in samples_data) + "\n")

        samples = parse_jsonl_samples(jsonl_file)

        assert len(samples) == 3
        assert samples[0]["tool_name"] == "Bash"
        assert samples[1]["tool_name"] == "Read"
        assert samples[2]["tool_name"] == "Edit"


class TestAnalyzeScriptHandlesMalformedJson:
    """Test that the analysis script gracefully handles malformed JSON."""

    def test_skips_malformed_lines(self, tmp_path: Path):
        """Script gracefully skips malformed JSON lines."""
        from hooks.scripts.analyze_hook_input import parse_jsonl_samples

        jsonl_file = tmp_path / "samples.jsonl"
        content = '{"tool_name": "Bash", "tool_input": {"command": "ls"}}\n'
        content += "not valid json\n"
        content += '{"tool_name": "Read", "tool_input": {"file_path": "/tmp/test.py"}}\n'
        jsonl_file.write_text(content)

        samples = parse_jsonl_samples(jsonl_file)

        assert len(samples) == 2
        assert samples[0]["tool_name"] == "Bash"
        assert samples[1]["tool_name"] == "Read"


class TestAnalyzeScriptIdentifiesRequiredFields:
    """Test that analysis identifies fields present in ALL samples."""

    def test_identifies_required_fields(self):
        """Script identifies fields present in all samples as required."""
        from hooks.scripts.analyze_hook_input import analyze_field_presence

        samples = [
            {"tool_name": "Bash", "tool_input": {"command": "ls"}, "session_id": "abc"},
            {"tool_name": "Read", "tool_input": {"file_path": "/tmp"}, "session_id": "def"},
            {"tool_name": "Edit", "tool_input": {"file_path": "/tmp"}, "session_id": "ghi"},
        ]

        analysis = analyze_field_presence(samples)

        assert "tool_name" in analysis["required"]
        assert "tool_input" in analysis["required"]
        assert "session_id" in analysis["required"]


class TestAnalyzeScriptIdentifiesOptionalFields:
    """Test that analysis identifies fields present in SOME samples."""

    def test_identifies_optional_fields(self):
        """Script identifies fields present in some samples as optional."""
        from hooks.scripts.analyze_hook_input import analyze_field_presence

        samples = [
            {"tool_name": "Bash", "tool_input": {"command": "ls"}, "session_id": "abc"},
            {"tool_name": "Read", "tool_input": {"file_path": "/tmp"}},  # No session_id
            {"tool_name": "Edit", "tool_input": {"file_path": "/tmp"}, "extra_field": "value"},
        ]

        analysis = analyze_field_presence(samples)

        assert "tool_name" in analysis["required"]
        assert "tool_input" in analysis["required"]
        assert "session_id" in analysis["optional"]
        assert "extra_field" in analysis["optional"]


class TestSchemaValidatesSampleData:
    """Test that PreToolUseHookData schema validates captured samples."""

    def test_schema_validates_bash_sample(self):
        """PreToolUseHookData validates a Bash tool sample."""
        from formaltask.hooks.input_schema import PreToolUseHookData

        sample = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
        }

        # Should not raise
        data = PreToolUseHookData.model_validate(sample)
        assert data.tool_name == "Bash"
        assert data.tool_input["command"] == "ls -la"

    def test_schema_validates_all_real_captured_samples(self, tmp_path):
        """PreToolUseHookData validates ALL 21 captured samples from Task #1698."""
        from pathlib import Path

        from formaltask.hooks.input_schema import PreToolUseHookData
        from hooks.scripts.analyze_hook_input import parse_jsonl_samples

        # Use real samples file if available, otherwise use embedded test samples
        samples_file = Path.home() / ".claude" / "hook-input-samples.jsonl"
        if samples_file.exists():
            samples = parse_jsonl_samples(samples_file)
        else:
            # Embedded representative samples for CI environments
            samples = [
                {"tool_name": "Bash", "tool_input": {"command": "echo test"}},
                {"tool_name": "Read", "tool_input": {"file_path": "/tmp/test.py"}},
                {"tool_name": "Write", "tool_input": {"file_path": "/tmp/x.py", "content": "x"}},
            ]

        # Validate ALL samples - schema must accept every one
        assert len(samples) >= 3, "Need at least 3 samples for meaningful test"
        for i, sample in enumerate(samples):
            data = PreToolUseHookData.model_validate(sample)
            assert data.tool_name == sample["tool_name"], f"Sample {i} tool_name mismatch"
            assert data.tool_input == sample["tool_input"], f"Sample {i} tool_input mismatch"


class TestSchemaRejectsInvalidData:
    """Test that PreToolUseHookData rejects malformed input."""

    def test_schema_rejects_missing_tool_name(self):
        """Schema rejects data missing required tool_name field."""
        from pydantic import ValidationError

        from formaltask.hooks.input_schema import PreToolUseHookData

        sample = {"tool_input": {"command": "ls"}}

        with pytest.raises(ValidationError) as exc_info:
            PreToolUseHookData.model_validate(sample)

        assert "tool_name" in str(exc_info.value)

    def test_schema_rejects_invalid_tool_input_type(self):
        """Schema rejects non-dict tool_input values."""
        from pydantic import ValidationError

        from formaltask.hooks.input_schema import PreToolUseHookData

        sample = {"tool_name": "Bash", "tool_input": "not a dict"}

        with pytest.raises(ValidationError) as exc_info:
            PreToolUseHookData.model_validate(sample)

        assert "tool_input" in str(exc_info.value)


class TestParseJsonlEdgeCases:
    """Test edge cases in JSONL parsing."""

    def test_parses_empty_jsonl_file(self, tmp_path: Path):
        """Script returns empty list for empty JSONL file."""
        from hooks.scripts.analyze_hook_input import parse_jsonl_samples

        jsonl_file = tmp_path / "empty.jsonl"
        jsonl_file.write_text("")

        samples = parse_jsonl_samples(jsonl_file)

        assert samples == []


class TestAnalyzeFieldPresenceEdgeCases:
    """Test edge cases in field presence analysis."""

    def test_returns_empty_analysis_for_empty_samples(self):
        """analyze_field_presence returns empty analysis for empty list."""
        from hooks.scripts.analyze_hook_input import analyze_field_presence

        analysis = analyze_field_presence([])

        assert analysis["required"] == []
        assert analysis["optional"] == []
        assert analysis["types"] == {}


class TestSchemaExtraFieldsBehavior:
    """Test that extra='allow' preserves unknown fields."""

    def test_schema_preserves_extra_fields(self):
        """Schema preserves unknown fields due to extra='allow' config."""
        from formaltask.hooks.input_schema import PreToolUseHookData

        sample = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "session_id": "abc123",
            "future_field": "some_value",
        }

        data = PreToolUseHookData.model_validate(sample)

        # Required fields present
        assert data.tool_name == "Bash"
        assert data.tool_input == {"command": "ls"}
        # Extra fields preserved via model_extra
        assert data.model_extra["session_id"] == "abc123"
        assert data.model_extra["future_field"] == "some_value"
