"""Mock fixtures for FormalTask tests (Task #1653).

Extracted from conftest.py to provide modular, focused fixture organization.
These fixtures mock external services (GitHub CLI).

Fixtures provided:
- mock_gh_cli: Mocks GitHub CLI subprocess calls (success)
- mock_gh_cli_failure: Mocks GitHub CLI subprocess calls (failure)
- skip_sqlite: Skip SQLite operations, fall back to JSON storage
"""

import subprocess

import pytest

# ============================================================================
# GitHub CLI Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_gh_cli(mocker):
    """Mock gh CLI subprocess calls.

    Returns:
        Mock: subprocess.run mock that returns success (returncode=0).

    Usage:
        def test_subprocess_success(mock_gh_cli):
            # Call code that uses subprocess
            result = subprocess.run(["gh", "issue", "list"])
            mock_gh_cli.assert_called_once()
    """
    mock = mocker.patch("subprocess.run")
    mock.return_value = subprocess.CompletedProcess(
        args=["gh", "issue", "edit"], returncode=0, stdout="", stderr=""
    )
    return mock


@pytest.fixture
def mock_gh_cli_failure(mocker):
    """Mock gh CLI subprocess calls that fail.

    Returns:
        Mock: subprocess.run mock that returns failure (returncode=1).

    Usage:
        def test_subprocess_failure(mock_gh_cli_failure):
            # Test code handles subprocess failures correctly
            result = subprocess.run(["gh", "issue", "edit"])
            assert result.returncode == 1
    """
    mock = mocker.patch("subprocess.run")
    mock.return_value = subprocess.CompletedProcess(
        args=["gh", "issue", "edit"], returncode=1, stdout="", stderr="Error: Issue not found"
    )
    return mock


# ============================================================================
# SQLite Skip Fixtures
# ============================================================================


@pytest.fixture
def skip_sqlite(monkeypatch):
    """Skip SQLite operations by making get_db_path() raise FileNotFoundError.

    This fixture causes state_manager and other SQLite-using code to fall back
    to JSON file storage. Useful for testing JSON fallback paths or when tests
    don't need SQLite behavior.

    Usage:
        def test_json_fallback(skip_sqlite):
            # Code will use JSON file storage instead of SQLite
            update_state_on_valid_handoff(42, {"phase": "ready"})

        def test_with_skip(skip_sqlite, tmp_path):
            # Combine with tmp_path for isolated JSON file tests
            ...
    """

    def _raise_file_not_found():
        raise FileNotFoundError("skip_sqlite fixture: no database")

    monkeypatch.setattr("formaltask.db.path.get_db_path", _raise_file_not_found)
