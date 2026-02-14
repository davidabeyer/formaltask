"""Unit tests for doc_guard_config module."""

import os
from unittest.mock import patch

import pytest

import formaltask.validators.doc_guard_config as dgc
from formaltask.validators.doc_guard_config import DocGuardConfig, DocumentedArea


class TestDocumentedAreaModel:
    """Tests for DocumentedArea Pydantic model."""

    def test_documented_area_model_validates_pattern_target(self):
        """DocumentedArea validates pattern and target fields."""
        area = DocumentedArea(pattern="hooks/lib/", target="hooks/CLAUDE.md")
        assert area.pattern == "hooks/lib/"
        assert area.target == "hooks/CLAUDE.md"

    def test_documented_area_rejects_empty_pattern(self):
        """DocumentedArea rejects empty pattern."""
        with pytest.raises(ValueError):
            DocumentedArea(pattern="", target="hooks/CLAUDE.md")

    def test_documented_area_rejects_empty_target(self):
        """DocumentedArea rejects empty target."""
        with pytest.raises(ValueError):
            DocumentedArea(pattern="hooks/lib/", target="")


class TestDocGuardConfig:
    """Tests for DocGuardConfig Pydantic model."""

    def test_with_defaults_returns_working_config(self):
        """with_defaults() returns working config with all documented areas."""
        config = DocGuardConfig.with_defaults()

        expected_patterns = {
            "hooks/lib/",
            "hooks/session_end/",
            "hooks/session_start/",
            "hooks/cli/",
            "hooks/cli/commands/",
            ".claude/skills/",
            ".claude/commands/",
            ".claude/agents/",
        }
        actual_patterns = {area.pattern for area in config.documented_areas}
        assert actual_patterns == expected_patterns


class TestLoadConfig:
    """Tests for load_config() function."""

    def test_load_config_valid_yaml_returns_config(self, tmp_path):
        """load_config() returns DocGuardConfig from valid YAML."""
        from formaltask.validators.doc_guard_config import load_config

        dgc._config_cache = None
        config_file = tmp_path / ".doc-guard.yaml"
        config_file.write_text(
            """
documented_areas:
  - pattern: "hooks/lib/"
    target: "hooks/CLAUDE.md"
"""
        )

        with patch.dict(os.environ, {"PROJECT_ROOT": str(tmp_path)}):
            config = load_config()

        assert len(config.documented_areas) == 1
        assert config.documented_areas[0].pattern == "hooks/lib/"

    def test_load_config_missing_file_returns_defaults(self, tmp_path):
        """load_config() returns defaults when file is missing."""
        from formaltask.validators.doc_guard_config import load_config

        dgc._config_cache = None
        with patch.dict(os.environ, {"PROJECT_ROOT": str(tmp_path)}):
            config = load_config()

        assert len(config.documented_areas) == 8

    def test_load_config_rejects_relative_project_root(self):
        """load_config() raises ValueError if PROJECT_ROOT is relative path."""
        from formaltask.validators.doc_guard_config import load_config

        dgc._config_cache = None
        with (
            patch.dict(os.environ, {"PROJECT_ROOT": "relative/path"}),
            pytest.raises(ValueError, match="PROJECT_ROOT must be an absolute path"),
        ):
            load_config(force_reload=True)

    def test_load_config_rejects_nonexistent_project_root(self):
        """load_config() raises ValueError if PROJECT_ROOT doesn't exist."""
        from formaltask.validators.doc_guard_config import load_config

        dgc._config_cache = None
        nonexistent = "/nonexistent/path/that/does/not/exist"
        with (
            patch.dict(os.environ, {"PROJECT_ROOT": nonexistent}),
            pytest.raises(ValueError, match="PROJECT_ROOT does not exist"),
        ):
            load_config(force_reload=True)


class TestGetTargetForFile:
    """Tests for get_target_for_file() function."""

    def test_get_target_for_file_hooks_lib_returns_claude_md(self, tmp_path):
        """get_target_for_file() returns hooks/CLAUDE.md for hooks/lib/ files (with defaults)."""
        from formaltask.validators.doc_guard_config import get_target_for_file

        dgc._config_cache = None
        with patch.dict(os.environ, {"PROJECT_ROOT": str(tmp_path)}):
            target = get_target_for_file("hooks/lib/foo.py")
        assert target == "hooks/CLAUDE.md"

    def test_get_target_for_file_unknown_path_returns_none(self, tmp_path):
        """get_target_for_file() returns None for unknown paths."""
        from formaltask.validators.doc_guard_config import get_target_for_file

        dgc._config_cache = None
        with patch.dict(os.environ, {"PROJECT_ROOT": str(tmp_path)}):
            target = get_target_for_file("random/unknown/path.py")
        assert target is None

    def test_get_target_for_file_uses_longest_match(self, tmp_path):
        """get_target_for_file() matches longest pattern when patterns overlap."""
        from formaltask.validators.doc_guard_config import get_target_for_file

        dgc._config_cache = None
        config_file = tmp_path / ".doc-guard.yaml"
        config_file.write_text(
            """
documented_areas:
  - pattern: "src/"
    target: "src/README.md"
  - pattern: "src/utils/"
    target: "src/utils/README.md"
"""
        )

        with patch.dict(os.environ, {"PROJECT_ROOT": str(tmp_path)}):
            # File in nested path should match longer pattern
            target = get_target_for_file("src/utils/helpers.py")
        assert target == "src/utils/README.md"


class TestMatchesDocumentedArea:
    """Tests for matches_documented_area() function."""

    def test_matches_documented_area_hooks_lib_returns_true(self, tmp_path):
        """matches_documented_area() returns True for hooks/lib/ files."""
        from formaltask.validators.doc_guard_config import matches_documented_area

        dgc._config_cache = None
        with patch.dict(os.environ, {"PROJECT_ROOT": str(tmp_path)}):
            assert matches_documented_area("hooks/lib/foo.py") is True

    def test_matches_documented_area_random_path_returns_false(self, tmp_path):
        """matches_documented_area() returns False for random paths."""
        from formaltask.validators.doc_guard_config import matches_documented_area

        dgc._config_cache = None
        with patch.dict(os.environ, {"PROJECT_ROOT": str(tmp_path)}):
            assert matches_documented_area("random/unknown/path.py") is False


class TestGetTargetForFileUsesCustomConfig:
    """Tests for get_target_for_file() using custom config."""

    def test_get_target_for_file_uses_custom_config_not_defaults(self, tmp_path):
        """get_target_for_file() should use load_config(), not with_defaults()."""
        from formaltask.validators.doc_guard_config import get_target_for_file

        dgc._config_cache = None
        config_file = tmp_path / ".doc-guard.yaml"
        config_file.write_text(
            """
documented_areas:
  - pattern: "custom/special/"
    target: "custom/CLAUDE.md"
"""
        )

        with patch.dict(os.environ, {"PROJECT_ROOT": str(tmp_path)}):
            target = get_target_for_file("custom/special/file.py")

        assert target == "custom/CLAUDE.md"


class TestLoadConfigExceptionHandling:
    """Tests for load_config() exception handling."""

    def test_load_config_yaml_error_logs_warning_and_returns_defaults(self, tmp_path, caplog):
        """load_config() logs warning on YAML parse error and returns defaults."""
        import logging

        from formaltask.validators.doc_guard_config import load_config

        dgc._config_cache = None
        config_file = tmp_path / ".doc-guard.yaml"
        config_file.write_text("invalid: yaml: content: [")

        with (
            patch.dict(os.environ, {"PROJECT_ROOT": str(tmp_path)}),
            caplog.at_level(logging.WARNING),
        ):
            config = load_config()

        assert len(config.documented_areas) == 8
        assert any("Failed to load" in record.message for record in caplog.records)

    def test_load_config_catches_specific_exceptions_not_bare_except(self, tmp_path):
        """load_config() should catch specific exceptions, not bare except."""
        from formaltask.validators.doc_guard_config import load_config

        dgc._config_cache = None
        config_file = tmp_path / ".doc-guard.yaml"
        config_file.write_text(
            """
documented_areas:
  - pattern: "test/"
    target: "test/CLAUDE.md"
"""
        )

        with (
            patch.dict(os.environ, {"PROJECT_ROOT": str(tmp_path)}),
            patch("yaml.safe_load", side_effect=RuntimeError("Unexpected error")),
            pytest.raises(RuntimeError, match="Unexpected error"),
        ):
            load_config()
