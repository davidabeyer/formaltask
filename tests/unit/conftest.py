"""Unit test fixtures for hooks/tests/unit/.

Provides fixtures for reducing mock boilerplate in tests.
"""

import subprocess
import sys

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
