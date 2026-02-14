"""Tests for subprocess environment variable whitelisting (Task #986).

Provides secure environment variable handling for subprocess calls
to prevent leaking sensitive or attacker-controlled environment variables.
"""

import os
from unittest.mock import patch


class TestBuildSubprocessEnv:
    """Tests for build_subprocess_env() function."""

    def test_includes_default_allowed_vars(self):
        """Should include standard system variables when present in os.environ."""
        from formaltask.utils.subprocess import build_subprocess_env

        with patch.dict(
            os.environ,
            {
                "PATH": "/usr/bin",
                "HOME": "/home/user",
                "USER": "testuser",
                "LANG": "en_US.UTF-8",
                "LC_ALL": "en_US.UTF-8",
                "PYTHONPATH": "/custom/path",
            },
            clear=True,
        ):
            result = build_subprocess_env()

        assert result["PATH"] == "/usr/bin"
        assert result["HOME"] == "/home/user"
        assert result["USER"] == "testuser"
        assert result["LANG"] == "en_US.UTF-8"
        assert result["LC_ALL"] == "en_US.UTF-8"
        assert result["PYTHONPATH"] == "/custom/path"

    def test_excludes_non_whitelisted_vars(self):
        """Should NOT include variables not in the whitelist."""
        from formaltask.utils.subprocess import build_subprocess_env

        with patch.dict(
            os.environ,
            {
                "PATH": "/usr/bin",
                "SECRET_KEY": "super-secret-value",  # pragma: allowlist secret
                "AWS_ACCESS_KEY_ID": "AKIA...",
                "DATABASE_PASSWORD": "password123",  # pragma: allowlist secret
                "ATTACKER_VAR": "malicious-value",
            },
            clear=True,
        ):
            result = build_subprocess_env()

        assert "SECRET_KEY" not in result
        assert "AWS_ACCESS_KEY_ID" not in result
        assert "DATABASE_PASSWORD" not in result
        assert "ATTACKER_VAR" not in result
        # But PATH should still be included
        assert result["PATH"] == "/usr/bin"

    def test_additional_vars_are_added(self):
        """Should allow adding extra variables via additional_vars parameter."""
        from formaltask.utils.subprocess import build_subprocess_env

        with patch.dict(os.environ, {"PATH": "/usr/bin"}, clear=True):
            result = build_subprocess_env(
                additional_vars={
                    "LLM_API_KEY": "sk-123",  # pragma: allowlist secret
                    "LLM_PROVIDER": "openai",
                }
            )

        assert result["PATH"] == "/usr/bin"
        assert result["LLM_API_KEY"] == "sk-123"  # pragma: allowlist secret
        assert result["LLM_PROVIDER"] == "openai"

    def test_extra_whitelist_vars_are_included(self):
        """Should allow extending whitelist via extra_whitelist parameter."""
        from formaltask.utils.subprocess import build_subprocess_env

        with patch.dict(
            os.environ,
            {
                "PATH": "/usr/bin",
                "CUSTOM_VAR": "custom-value",
                "ANOTHER_VAR": "another-value",
            },
            clear=True,
        ):
            result = build_subprocess_env(extra_whitelist=["CUSTOM_VAR", "ANOTHER_VAR"])

        assert result["CUSTOM_VAR"] == "custom-value"
        assert result["ANOTHER_VAR"] == "another-value"

    def test_additional_vars_override_extra_whitelist(self):
        """Explicit additional_vars should take precedence over environment values."""
        from formaltask.utils.subprocess import build_subprocess_env

        with patch.dict(
            os.environ,
            {
                "PATH": "/usr/bin",
                "CONFLICT_VAR": "from_environment",
            },
            clear=True,
        ):
            result = build_subprocess_env(
                additional_vars={"CONFLICT_VAR": "explicit_value"},
                extra_whitelist=["CONFLICT_VAR"],
            )

        # additional_vars applied LAST, so explicit value wins
        assert result["CONFLICT_VAR"] == "explicit_value"


class TestDefaultWhitelist:
    """Tests for the default whitelist constant."""

    def test_default_whitelist_matches_session_end_worker(self):
        """Default whitelist should include the same vars as session_end_worker.py cognify code."""
        from formaltask.utils.subprocess import DEFAULT_ENV_WHITELIST

        # These are the vars from session_end_worker.py lines 1137
        session_end_vars = ["PATH", "HOME", "USER", "LANG", "LC_ALL", "PYTHONPATH"]

        for var in session_end_vars:
            assert var in DEFAULT_ENV_WHITELIST, (
                f"{var} from session_end_worker.py should be in DEFAULT_ENV_WHITELIST"
            )
