#!/usr/bin/env python3
"""Tests for tool_redirect validator."""

import pytest


class TestToolRedirectValidator:
    """Test suite for tool_redirect validator using rules kernel."""

    def test_blocks_websearch(self):
        """Should block WebSearch and return block decision."""
        from formaltask.validators.tool_redirect import check

        result = check({"tool_name": "WebSearch", "tool_input": {"query": "test"}})

        assert result is not None
        assert result["decision"] == "block"
        assert "exa" in result["reason"].lower()

    def test_allows_other_tools(self):
        """Should return None for non-WebSearch tools."""
        from formaltask.validators.tool_redirect import check

        result = check({"tool_name": "WebFetch", "tool_input": {"url": "https://example.com"}})
        assert result is None

    def test_allows_read_tool(self):
        """Should return None for Read tool."""
        from formaltask.validators.tool_redirect import check

        result = check({"tool_name": "Read", "tool_input": {"file_path": "/tmp/test.txt"}})
        assert result is None

    def test_allows_bash_tool(self):
        """Should return None for Bash tool."""
        from formaltask.validators.tool_redirect import check

        result = check({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        assert result is None

    def test_block_reason_message(self):
        """Should have specific message about using exa."""
        from formaltask.validators.tool_redirect import check

        result = check({"tool_name": "WebSearch", "tool_input": {"query": "test query"}})

        assert result is not None
        assert "WebSearch not allowed" in result["reason"]
        assert "exa" in result["reason"].lower()

    def test_missing_tool_name(self):
        """Should return None for missing tool_name."""
        from formaltask.validators.tool_redirect import check

        result = check({"tool_input": {"query": "test"}})
        assert result is None


class TestToolRedirectRules:
    """Test TOOL_REDIRECT_RULES are properly defined."""

    def test_rules_exist(self):
        """Should have at least one tool redirect rule."""
        from formaltask.core.rules_builtin import TOOL_REDIRECT_RULES

        assert len(TOOL_REDIRECT_RULES) >= 1

    def test_websearch_rule_exists(self):
        """Should have a WebSearch blocking rule."""
        from formaltask.core.rules_builtin import TOOL_REDIRECT_RULES

        websearch_rules = [r for r in TOOL_REDIRECT_RULES if "WebSearch" in r.when]
        assert len(websearch_rules) >= 1

    def test_rule_has_block_target(self):
        """WebSearch rule should have tool.block target."""
        from formaltask.core.rules_builtin import TOOL_REDIRECT_RULES

        websearch_rules = [r for r in TOOL_REDIRECT_RULES if "WebSearch" in r.when]
        assert websearch_rules[0].target == "tool.block"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
