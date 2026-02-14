"""Security hardening tests for Task #1526.

TDD Red Phase: Write one test, see it fail, implement, repeat.
"""


class TestPathComparison:
    """Tests for secure path comparison."""

    def test_path_matching_rejects_prefix_attacks(self, monkeypatch):
        """Path matching should not match prefix-similar but different directories."""
        from formaltask.validators import doc_guard_config

        # Mock config with a pattern that could have false positives
        mock_area = type("MockArea", (), {"pattern": "hooks/lib", "target": "hooks/CLAUDE.md"})()
        mock_config = type("MockConfig", (), {"documented_areas": [mock_area]})()
        monkeypatch.setattr(doc_guard_config, "load_config", lambda: mock_config)

        # This should NOT match - it's a different directory with similar prefix
        from formaltask.validators.doc_guard_config import get_target_for_file

        result = get_target_for_file("hooks/lib_malicious/evil.py")
        assert result is None, "Prefix attack should not match"
