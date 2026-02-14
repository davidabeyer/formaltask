"""Unit test fixtures for hooks/tests/unit/.

Provides fixtures for reducing mock boilerplate in doc_analyzer_worker tests.
"""

import json
import subprocess
import sys
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest

from tests.fixtures.paths import SESSION_END_DIR


@pytest.fixture
def git_repo(tmp_path):
    """Create a temp git repo with one commit.

    Eliminates ~15 lines of repeated setup in git integration tests.
    """
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    return tmp_path


# Add project paths for imports
sys.path.insert(0, str(SESSION_END_DIR))


@pytest.fixture
def doc_analyzer_env(tmp_path, monkeypatch):
    """Set up environment for doc_analyzer_worker tests.

    Configures PROJECT_ROOT and OPENROUTER_API_KEY environment variables.
    Returns tmp_path for assertions about file locations.

    Usage:
        def test_writes_to_project_root(doc_analyzer_env):
            project_root = doc_analyzer_env
            # ... run test ...
            pending_file = project_root / ".claude" / "doc-guard" / "pending.json"
            assert pending_file.exists()
    """
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    return tmp_path


@contextmanager
def mock_doc_analyzer_main(
    stdin_data: dict,
    commits: list = None,
    documented_files: list = None,
    analysis_result=None,
    analyzed_commits: set = None,
):
    """Context manager that patches doc_analyzer_worker dependencies.

    Consolidates 6-7 patches into a single context manager, reducing
    test boilerplate while maintaining full control over mock behavior.

    Args:
        stdin_data: Dict to be JSON-serialized as stdin input
        commits: List of commit dicts for get_session_commits (default: empty)
        documented_files: List of file paths for filter_documented_files (default: empty)
        analysis_result: DocAnalysisResult for analyze_commits (default: None)
        analyzed_commits: Set of already-analyzed commit hashes (default: empty set)

    Yields:
        dict: Mocks dict with all 7 patched dependencies:
            - write_pending: mock for write_pending()
            - analyze_commits: mock for analyze_commits()
            - get_client: mock for get_openrouter_client()
            - client: the mock client object
            - get_session_commits: mock for get_session_commits()
            - filter_documented_files: mock for filter_documented_files()
            - load_analyzed_commits: mock for load_analyzed_commits()

    Usage:
        def test_main_calls_write(doc_analyzer_env):
            from doc_analyzer_worker import main, DocAnalysisResult

            result = DocAnalysisResult(needs_update=True, suggestions=[], summary="Test summary here")

            with mock_doc_analyzer_main(
                stdin_data={"session_id": "test-123"},
                commits=[{"hash": "abc", "message": "Add", "files": ["hooks/lib/x.py"]}],
                documented_files=["hooks/lib/x.py"],
                analysis_result=result,
            ) as mocks:
                exit_code = main()

            assert exit_code == 0
            mocks["write_pending"].assert_called_once()
    """
    commits = commits or []
    documented_files = documented_files or []
    analyzed_commits = analyzed_commits or set()

    mock_client = Mock()

    with (
        patch("sys.stdin.read", return_value=json.dumps(stdin_data)),
        patch(
            "doc_analyzer_worker.get_openrouter_client",
            return_value=(mock_client, "google/gemini-2.5-pro"),
        ) as mock_get_client,
        patch(
            "doc_analyzer_worker.get_session_commits",
            return_value=commits,
        ) as mock_get_commits,
        patch(
            "doc_analyzer_worker.filter_documented_files",
            return_value=documented_files,
        ) as mock_filter_files,
        patch(
            "doc_analyzer_worker.analyze_commits",
            return_value=analysis_result,
        ) as mock_analyze,
        patch("doc_analyzer_worker.write_pending") as mock_write,
        patch(
            "doc_analyzer_worker.load_analyzed_commits",
            return_value=analyzed_commits,
        ) as mock_load_analyzed,
    ):
        yield {
            "write_pending": mock_write,
            "analyze_commits": mock_analyze,
            "get_client": mock_get_client,
            "client": mock_client,
            "get_session_commits": mock_get_commits,
            "filter_documented_files": mock_filter_files,
            "load_analyzed_commits": mock_load_analyzed,
        }
