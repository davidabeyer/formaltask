"""Tests for openrouter_client module - OpenRouter/Instructor-based LLM client."""

import pytest


class TestLoadApiKey:
    """Test API key loading from environment variable."""

    def test_loads_from_environment_variable(self, monkeypatch):
        """API key should be loaded from OPENROUTER_API_KEY env var."""
        from formaltask.llm.openrouter import _load_api_key

        test_key = "sk-or-test-openrouter-key"
        monkeypatch.setenv("OPENROUTER_API_KEY", test_key)

        result = _load_api_key()

        assert result == test_key

    def test_raises_value_error_when_no_key_found(self, monkeypatch, tmp_path):
        """Should raise ValueError with helpful message when key not found."""
        from pathlib import Path

        from formaltask.llm.openrouter import _load_api_key

        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        # Mock home to avoid finding real ~/.claude.json
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        with pytest.raises(ValueError) as exc_info:
            _load_api_key()

        assert "OPENROUTER_API_KEY not found" in str(exc_info.value)

    def test_strips_whitespace_from_key(self, monkeypatch):
        """API key should have whitespace stripped."""
        from formaltask.llm.openrouter import _load_api_key

        monkeypatch.setenv("OPENROUTER_API_KEY", "  sk-or-key-with-spaces\n  ")

        result = _load_api_key()

        assert result == "sk-or-key-with-spaces"

    def test_loads_from_claude_json_when_env_not_set(self, monkeypatch, tmp_path):
        """Should load API key from ~/.claude.json mcpServers env when env var not set."""
        import json
        from pathlib import Path

        from formaltask.llm.openrouter import _load_api_key

        # Clear env var
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

        # Create mock ~/.claude.json with nested structure (like real file)
        claude_json = tmp_path / ".claude.json"
        config = {
            "mcpServers": {
                "some-server": {
                    "env": {
                        "OPENROUTER_API_KEY": "sk-or-from-claude-json"  # pragma: allowlist secret
                    }
                }
            }
        }
        claude_json.write_text(json.dumps(config))

        # Monkeypatch Path.home() to return tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = _load_api_key()

        assert result == "sk-or-from-claude-json"


