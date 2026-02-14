#!/usr/bin/env python3
"""Direct unit tests for get_target_for_file() algorithm.

These tests verify the longest-prefix matching algorithm directly,
testing edge cases and algorithm behavior without mocking.

Tests use a controlled config via the use_test_config fixture
to isolate algorithm tests from real .doc-guard.yaml changes.
"""

import shutil

import pytest

import formaltask.validators.doc_guard_config as dgc
from tests.fixtures.paths import FIXTURES_DIR


@pytest.fixture
def use_test_config(tmp_path, monkeypatch):
    """Use the test fixture .doc-guard.yaml for algorithm tests."""
    shutil.copy(FIXTURES_DIR / ".doc-guard.yaml", tmp_path / ".doc-guard.yaml")
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    dgc._config_cache = None
    yield tmp_path
    dgc._config_cache = None


class TestGetTargetForFileAlgorithm:
    """Direct tests for get_target_for_file() longest-prefix algorithm."""

    def test_basic_matching_returns_target(self, use_test_config):
        """File under a documented pattern returns the target."""
        from formaltask.validators.doc_guard_config import get_target_for_file

        result = get_target_for_file("hooks/lib/file.py")
        assert result == "hooks/CLAUDE.md"

    def test_longest_prefix_wins(self, use_test_config):
        """When multiple patterns match, longest prefix wins.

        Test config has:
        - hooks/lib/ -> hooks/CLAUDE.md
        - hooks/cli/ -> hooks/cli/CLAUDE.md
        - hooks/ -> hooks/CLAUDE.md (fallback)
        """
        from formaltask.validators.doc_guard_config import get_target_for_file

        # hooks/cli/ is more specific than hooks/
        result = get_target_for_file("hooks/cli/command.py")
        assert result == "hooks/cli/CLAUDE.md"

    def test_no_match_returns_none(self, use_test_config):
        """File outside all documented areas returns None."""
        from formaltask.validators.doc_guard_config import get_target_for_file

        result = get_target_for_file("random/path/file.py")
        assert result is None

    def test_empty_path_returns_none(self, use_test_config):
        """Empty string path returns None."""
        from formaltask.validators.doc_guard_config import get_target_for_file

        result = get_target_for_file("")
        assert result is None

    def test_trailing_slash_in_filepath_still_matches(self, use_test_config):
        """File path with trailing slash should still match pattern."""
        from formaltask.validators.doc_guard_config import get_target_for_file

        # Even with trailing slash, should match hooks/lib/ pattern
        result = get_target_for_file("hooks/lib/file.py/")
        # Algorithm uses startswith, trailing slash shouldn't break it
        assert result == "hooks/CLAUDE.md"

    def test_path_with_dot_prefix_normalized(self, use_test_config):
        """Path with ./ prefix is normalized before matching."""
        from formaltask.validators.doc_guard_config import get_target_for_file

        # Algorithm normalizes ./hooks/lib/ to hooks/lib/
        result = get_target_for_file("./hooks/lib/file.py")
        assert result == "hooks/CLAUDE.md"

    def test_path_with_parent_dir_not_normalized(self, use_test_config):
        """Path with .. is NOT normalized - matches raw string prefix.

        Note: This documents current behavior. The algorithm uses startswith
        on the raw string, so hooks/cli/../lib/ matches hooks/cli/ pattern
        because it literally starts with "hooks/cli/".
        """
        from formaltask.validators.doc_guard_config import get_target_for_file

        # Raw startswith: "hooks/cli/../lib/" starts with "hooks/cli/"
        result = get_target_for_file("hooks/cli/../lib/file.py")
        assert result == "hooks/cli/CLAUDE.md"  # Matches hooks/cli/, not hooks/lib/


class TestYAMLErrorHandling:
    """Tests for graceful YAML error handling in load_config()."""

    def test_malformed_yaml_returns_defaults(self, tmp_path, monkeypatch):
        """Malformed YAML falls back to defaults gracefully."""
        from formaltask.validators.doc_guard_config import load_config

        # Write malformed YAML
        config_file = tmp_path / ".doc-guard.yaml"
        config_file.write_text("{ invalid yaml: [")  # Unclosed bracket

        monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
        dgc._config_cache = None

        # Should return defaults, not raise
        config = load_config()
        assert len(config.documented_areas) > 0  # Has default areas
        dgc._config_cache = None

    def test_missing_required_keys_returns_defaults(self, tmp_path, monkeypatch):
        """YAML with missing pattern/target keys falls back gracefully."""
        from formaltask.validators.doc_guard_config import load_config

        # YAML with missing 'target' key in documented_areas
        config_file = tmp_path / ".doc-guard.yaml"
        config_file.write_text("""
documented_areas:
  - pattern: "hooks/lib/"
    # target key missing!
""")

        monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
        dgc._config_cache = None

        # Should fall back to defaults
        config = load_config()
        assert len(config.documented_areas) > 0
        dgc._config_cache = None

    def test_empty_yaml_file_returns_defaults(self, tmp_path, monkeypatch):
        """Empty YAML file falls back to defaults."""
        from formaltask.validators.doc_guard_config import load_config

        # Empty file
        config_file = tmp_path / ".doc-guard.yaml"
        config_file.write_text("")

        monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
        dgc._config_cache = None

        config = load_config()
        assert len(config.documented_areas) > 0  # Has default areas
        dgc._config_cache = None
