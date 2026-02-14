"""Unit tests for API error handling in doc_analyzer_worker.py (Task #1027)

Tests verify that API calls in analyze_commits() are wrapped in try/except,
log errors with stack trace, and return graceful fallback on error.

Note: Tests use openai.APIConnectionError to simulate real API failures.
Per Task #932, analyze_commits catches only specific API/network errors
(openai.APIError, httpx.RequestError, pydantic.ValidationError), allowing
programming errors to propagate.
"""

import json
import logging
import sys
from unittest.mock import Mock, patch

import openai

from tests.fixtures.paths import SESSION_END_DIR

# Add session-end to path
sys.path.insert(0, str(SESSION_END_DIR))


class TestAnalyzeCommitsApiErrorHandling:
    """Test API error handling in analyze_commits() function"""

    def test_analyze_commits_returns_none_on_api_error(self):
        """Test analyze_commits returns None when API call raises exception."""
        from doc_analyzer_worker import analyze_commits

        # Create mock client that raises an API connection error
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = openai.APIConnectionError(request=Mock())

        commits = [{"hash": "abc123", "message": "Add feature", "files": ["hooks/lib/new.py"]}]
        documented_files = ["hooks/lib/new.py"]
        model = "google/gemini-2.5-pro"

        # Should return None instead of raising
        result = analyze_commits(mock_client, model, commits, documented_files)

        assert result is None

    def test_analyze_commits_logs_error_with_traceback(self, caplog):
        """Test analyze_commits logs error message with stack trace on API failure."""
        from doc_analyzer_worker import analyze_commits

        # Create mock client that raises an API connection error
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = openai.APIConnectionError(request=Mock())

        commits = [{"hash": "def456", "message": "Fix bug", "files": ["hooks/lib/utils.py"]}]
        documented_files = ["hooks/lib/utils.py"]
        model = "google/gemini-2.5-pro"

        with caplog.at_level(logging.ERROR):
            analyze_commits(mock_client, model, commits, documented_files)

        # Should log error with exception info
        assert len(caplog.records) >= 1
        error_log = caplog.records[0]
        assert error_log.levelno == logging.ERROR
        assert "API error" in caplog.text or "APIConnectionError" in caplog.text


class TestMainApiErrorIntegration:
    """Integration test for main() handling API errors gracefully"""

    def test_main_exits_successfully_when_api_fails(self, monkeypatch, tmp_path):
        """Test main() exits with 0 and doesn't write pending when API call fails."""
        from doc_analyzer_worker import main

        monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        hook_data = json.dumps({"session_id": "test-api-failure"})

        # Mock client that raises an API connection error
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = openai.APIConnectionError(request=Mock())

        with (
            patch("sys.stdin.read", return_value=hook_data),
            patch(
                "doc_analyzer_worker.get_openrouter_client",
                return_value=(mock_client, "google/gemini-2.5-pro"),
            ),
            patch(
                "doc_analyzer_worker.get_session_commits",
                return_value=[{"hash": "abc", "message": "Test", "files": ["hooks/lib/x.py"]}],
            ),
            patch("doc_analyzer_worker.filter_documented_files", return_value=["hooks/lib/x.py"]),
            patch("doc_analyzer_worker.load_analyzed_commits", return_value=set()),
        ):
            exit_code = main()

        # Should exit successfully (graceful degradation)
        assert exit_code == 0

        # Should NOT write to pending.json (analyze_commits returned None)
        pending_file = tmp_path / ".claude" / "doc-guard" / "pending.json"
        assert not pending_file.exists()
