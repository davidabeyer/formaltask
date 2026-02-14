"""Tests for plugin discovery mechanism.

Task #1735: Add pytest tests for plugin discovery.
"""

from formaltask.cli.commands import discover_plugins


class TestDiscoverPlugins:
    """Tests for discover_plugins function."""

    def test_discover_plugins_finds_at_least_one_module(self):
        """discover_plugins finds at least one valid command module."""
        result = discover_plugins()
        assert isinstance(result, dict)
        assert len(result) > 0
