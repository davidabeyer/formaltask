"""Tests for path_audit.py - Path(__file__) pattern scanner for test reorganization.

TDD tests following Red-Green-Refactor workflow.
Task #2124: Pre-flight Checks and Path Pattern Audit
"""


class TestPathPatternScanner:
    """Tests for Path(__file__) pattern detection."""

    def test_scanner_import(self):
        """RED: Verify scanner module can be imported."""
        from hooks.scripts import path_audit

        assert hasattr(path_audit, "scan_for_path_file_patterns")

    def test_detects_path_dunder_file_pattern(self, tmp_path):
        """Test detection of Path(__file__) pattern."""
        from hooks.scripts.path_audit import scan_for_path_file_patterns

        # Create test file with pattern
        test_file = tmp_path / "test_module.py"
        test_file.write_text("""
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
""")

        result = scan_for_path_file_patterns(tmp_path)

        assert len(result) == 1
        assert result[0]["path"] == "test_module.py"
        assert len(result[0]["instances"]) == 1
        assert result[0]["instances"][0]["line"] == 4
        assert "Path(__file__)" in result[0]["instances"][0]["pattern"]


class TestJsonOutputSchema:
    """Tests for JSON output conforming to schema v1.0."""

    def test_generate_audit_json_schema_version(self, tmp_path):
        """Test that output includes schema_version 1.0."""
        from hooks.scripts.path_audit import generate_audit_json

        result = generate_audit_json([], tmp_path)

        assert result["schema_version"] == "1.0"

    def test_generate_audit_json_has_timestamp(self, tmp_path):
        """Test that output includes ISO8601 timestamp."""
        import re

        from hooks.scripts.path_audit import generate_audit_json

        result = generate_audit_json([], tmp_path)

        assert "audit_timestamp" in result
        iso8601_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        assert re.match(iso8601_pattern, result["audit_timestamp"])

    def test_generate_audit_json_includes_files_and_summary(self, tmp_path):
        """Test that output includes files array and summary counts."""
        from hooks.scripts.path_audit import generate_audit_json

        files = [
            {
                "path": "src/a.py",
                "instances": [
                    {"line": 1, "pattern": "Path(__file__)", "context": "..."},
                    {"line": 5, "pattern": "Path(__file__)", "context": "..."},
                ],
            },
            {
                "path": "src/b.py",
                "instances": [
                    {"line": 10, "pattern": "Path(__file__)", "context": "..."},
                ],
            },
        ]
        result = generate_audit_json(files, tmp_path)

        assert result["files"] == files
        assert result["summary"]["total_files"] == 2
        assert result["summary"]["total_instances"] == 3


class TestBaselineGeneration:
    """Tests for baseline.txt generation."""

    def test_generate_baseline_creates_sorted_list_with_test_files(self, tmp_path):
        """Test that baseline finds and sorts test files."""
        from hooks.scripts.path_audit import generate_baseline_txt

        # Create test directory structure
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_b.py").write_text("# test")
        (tests_dir / "test_a.py").write_text("# test")

        baseline = generate_baseline_txt(tmp_path)

        lines = [line for line in baseline.strip().split("\n") if line]
        assert len(lines) == 2
        assert "tests/test_a.py" in lines
        assert "tests/test_b.py" in lines
        assert lines == sorted(lines)

    def test_generate_baseline_includes_conftest(self, tmp_path):
        """Test that baseline includes conftest.py files."""
        from hooks.scripts.path_audit import generate_baseline_txt

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_a.py").write_text("# test")
        (tests_dir / "conftest.py").write_text("# fixtures")

        baseline = generate_baseline_txt(tmp_path)

        lines = [line for line in baseline.strip().split("\n") if line]
        assert "tests/conftest.py" in lines
        assert "tests/test_a.py" in lines


class TestMainFunction:
    """Integration tests for main() function."""

    def test_main_creates_output_files(self, tmp_path):
        """Test that main() creates both output files."""
        import json

        from hooks.scripts.path_audit import main

        # Create a test file with pattern
        (tmp_path / "test_file.py").write_text("ROOT = Path(__file__).parent")

        # Set up paths
        output_json = tmp_path / "path-audit-results.json"
        output_baseline = tmp_path / "baseline.txt"

        main(
            project_root=tmp_path,
            output_json_path=output_json,
            output_baseline_path=output_baseline,
        )

        assert output_json.exists()
        assert output_baseline.exists()

        # Verify JSON is valid
        with open(output_json) as f:
            data = json.load(f)
        assert data["schema_version"] == "1.0"
