#!/usr/bin/env python3
"""
Tests for auto-index SessionStart hook

Tests the auto_index_codebase module which detects stale code-search indices
and triggers background re-indexing.

Implements <!-- TEST-MOCKING --> pattern from CLAUDE.md.
"""

import time
from unittest.mock import patch

import pytest

# Check if mcp SDK is available (optional dependency for auto_index_worker tests)
try:
    import mcp  # noqa: F401

    HAS_MCP = True
except ImportError:
    HAS_MCP = False


class TestShouldReindex:
    """Tests for should_reindex() function"""

    def test_returns_true_when_never_indexed(self, tmp_path):
        """should_reindex() returns True when timestamp file doesn't exist"""
        from hooks.session_start.auto_index_codebase import should_reindex

        # Point to empty directory (no timestamp file = never indexed)
        with patch("hooks.session_start.auto_index_codebase.STATE_DIR", tmp_path):
            assert should_reindex() is True

    def test_returns_false_when_recently_indexed(self, tmp_path):
        """should_reindex() returns False when indexed within 4 hours"""
        from hooks.session_start.auto_index_codebase import should_reindex

        # Create a recent timestamp file
        timestamp_file = tmp_path / "last-index-timestamp"
        timestamp_file.write_text(str(time.time()))

        with patch("hooks.session_start.auto_index_codebase.STATE_DIR", tmp_path):
            assert should_reindex() is False

    def test_returns_true_when_stale(self, tmp_path):
        """should_reindex() returns True when last index > 4 hours ago"""
        from hooks.session_start.auto_index_codebase import (
            MIN_REINDEX_INTERVAL_HOURS,
            should_reindex,
        )

        # Create timestamp file with old timestamp
        timestamp_file = tmp_path / "last-index-timestamp"
        old_time = time.time() - (MIN_REINDEX_INTERVAL_HOURS + 1) * 3600
        timestamp_file.write_text(str(old_time))

        with patch("hooks.session_start.auto_index_codebase.STATE_DIR", tmp_path):
            assert should_reindex() is True


class TestIsWorkerRunning:
    """Tests for is_worker_running() function"""

    def test_returns_false_when_lock_file_missing(self, tmp_path):
        """Worker is not running when lock file doesn't exist"""
        from hooks.session_start.auto_index_codebase import is_worker_running

        # Point to empty directory (no lock file)
        with patch("hooks.session_start.auto_index_codebase.STATE_DIR", tmp_path):
            assert is_worker_running() is False

    def test_returns_true_when_lock_file_exists(self, tmp_path):
        """Worker is running when lock file exists"""
        from hooks.session_start.auto_index_codebase import is_worker_running

        # Create lock file
        lock_file = tmp_path / "reindex.lock"
        lock_file.write_text("")

        with patch("hooks.session_start.auto_index_codebase.STATE_DIR", tmp_path):
            assert is_worker_running() is True

    def test_returns_false_when_lock_file_stale(self, tmp_path):
        """Stale lock files (>1 hour old) should be auto-removed and return False.

        This prevents crashed workers from permanently blocking reindexing.
        """
        import os

        from hooks.session_start.auto_index_codebase import is_worker_running

        # Create lock file and backdate it beyond 1 hour
        lock_file = tmp_path / "reindex.lock"
        lock_file.write_text("")

        # Set mtime to 2 hours ago (well beyond 1 hour timeout)
        old_time = time.time() - 7200  # 2 hours ago
        os.utime(lock_file, (old_time, old_time))

        with patch("hooks.session_start.auto_index_codebase.STATE_DIR", tmp_path):
            # Should return False because lock is stale
            assert is_worker_running() is False
            # Lock file should have been removed
            assert not lock_file.exists()


class TestLoadClaudeContextEnv:
    """Tests for load_claude_context_env() function"""

    def test_loads_env_vars_from_claude_json(self, tmp_path):
        """Should load environment variables from ~/.claude.json mcpServers config."""
        import json

        from hooks.session_start.auto_index_codebase import load_claude_context_env

        # Create mock ~/.claude.json
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "claude-context": {
                            "type": "stdio",
                            "command": "npx",
                            "args": ["@zilliz/claude-context-mcp@latest"],
                            "env": {
                                "OPENAI_API_KEY": "sk-test-key",  # pragma: allowlist secret
                                "MILVUS_ADDRESS": "https://test.zilliz.com",
                                "MILVUS_TOKEN": "test-token",
                            },
                        }
                    }
                }
            )
        )

        with patch("hooks.session_start.auto_index_codebase.Path.home", return_value=tmp_path):
            env = load_claude_context_env()

        assert env["OPENAI_API_KEY"] == "sk-test-key"  # pragma: allowlist secret
        assert env["MILVUS_ADDRESS"] == "https://test.zilliz.com"
        assert env["MILVUS_TOKEN"] == "test-token"

    def test_returns_empty_dict_when_file_missing(self, tmp_path):
        """Should return empty dict if ~/.claude.json doesn't exist."""
        from hooks.session_start.auto_index_codebase import load_claude_context_env

        with patch("hooks.session_start.auto_index_codebase.Path.home", return_value=tmp_path):
            env = load_claude_context_env()

        assert env == {}


class TestSpawnWorker:
    """Tests for spawn_worker() function"""

    def test_creates_lock_file_on_spawn(self, tmp_path):
        """spawn_worker should create lock file before spawning process"""
        from hooks.session_start.auto_index_codebase import spawn_worker

        with (
            patch("hooks.session_start.auto_index_codebase.STATE_DIR", tmp_path),
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_popen.return_value.pid = 12345
            spawn_worker()

            # Lock file should exist
            lock_file = tmp_path / "reindex.lock"
            assert lock_file.exists()


@pytest.mark.skipif(not HAS_MCP, reason="mcp SDK not installed")
class TestAutoIndexWorker:
    """Tests for auto_index_worker.py background worker

    Note: These tests require the mcp SDK to be installed. They are skipped
    in CI environments where mcp is not available.
    """

    def test_worker_cleans_up_lock_file_on_success(self, tmp_path):
        """Worker should remove lock file after successful completion."""
        from hooks.session_start.auto_index_worker import run_reindex

        # Create lock file (simulating spawn_worker having created it)
        lock_file = tmp_path / "reindex.lock"
        lock_file.write_text("")

        with (
            patch("hooks.session_start.auto_index_worker.STATE_DIR", tmp_path),
            patch("hooks.session_start.auto_index_worker.call_index_codebase") as mock_call,
        ):
            mock_call.return_value = True
            run_reindex()

        # Lock file should be cleaned up
        assert not lock_file.exists()

    def test_worker_cleans_up_lock_file_on_failure(self, tmp_path):
        """Worker should remove lock file even when reindex fails."""
        from hooks.session_start.auto_index_worker import run_reindex

        # Create lock file
        lock_file = tmp_path / "reindex.lock"
        lock_file.write_text("")

        with (
            patch("hooks.session_start.auto_index_worker.STATE_DIR", tmp_path),
            patch("hooks.session_start.auto_index_worker.call_index_codebase") as mock_call,
        ):
            mock_call.side_effect = Exception("MCP connection failed")
            run_reindex()

        # Lock file should STILL be cleaned up even on failure
        assert not lock_file.exists()


class TestMain:
    """Tests for main() entry point"""

    def test_does_not_spawn_when_index_fresh(self, tmp_path):
        """main() should not spawn worker when index is fresh"""
        from hooks.session_start.auto_index_codebase import main

        # Create fresh timestamp file (index is not stale)
        timestamp_file = tmp_path / "last-index-timestamp"
        timestamp_file.write_text(str(time.time()))

        with (
            patch("hooks.session_start.auto_index_codebase.STATE_DIR", tmp_path),
            patch("hooks.session_start.auto_index_codebase.spawn_worker") as mock_spawn,
        ):
            main()
            mock_spawn.assert_not_called()

    def test_spawns_worker_when_index_stale(self, tmp_path):
        """main() should spawn worker when index is stale and no worker running"""
        from hooks.session_start.auto_index_codebase import main

        # No timestamp file means index is stale, no lock file means no worker running
        with (
            patch("hooks.session_start.auto_index_codebase.STATE_DIR", tmp_path),
            patch("hooks.session_start.auto_index_codebase.spawn_worker") as mock_spawn,
        ):
            main()
            mock_spawn.assert_called_once()

    def test_does_not_spawn_when_worker_running(self, tmp_path):
        """main() should not spawn worker when worker is already running"""
        from hooks.session_start.auto_index_codebase import main

        # No timestamp file = stale, but lock file exists = worker running
        lock_file = tmp_path / "reindex.lock"
        lock_file.write_text("")

        with (
            patch("hooks.session_start.auto_index_codebase.STATE_DIR", tmp_path),
            patch("hooks.session_start.auto_index_codebase.spawn_worker") as mock_spawn,
        ):
            main()
            mock_spawn.assert_not_called()
