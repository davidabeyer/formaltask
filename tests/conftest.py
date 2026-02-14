"""Shared pytest fixtures and test helpers for FormalTask test suite.

Modular Fixtures (loaded via pytest_plugins):
- fixtures/database.py: Database fixtures (db_path, session_db, etc.)
- fixtures/mocks.py: Mock fixtures (mock_gh_cli, mock_openrouter_client, etc.)

Testing Guidelines:
- NEVER call real external services (MCP, GitHub, file system)
- Use in-memory SQLite (:memory:) for database tests
- Mock all subprocess calls (gh CLI, git, etc.)
- Use tmp_path for file operations
"""

# PYTHONPATH setup for hooks module imports
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set PROJECT_ROOT env var BEFORE any hooks modules are imported
os.environ["PROJECT_ROOT"] = str(PROJECT_ROOT)

import json

import pytest

# Load modular fixtures via fixtures/__init__.py
pytest_plugins = [
    "tests.fixtures",
]


@pytest.fixture(autouse=True)
def clear_doc_guard_config_cache():
    """Clear doc-guard config cache before each test.

    The load_config() function caches configuration at module level to avoid
    repeated YAML parsing. This fixture ensures test isolation by clearing
    the cache before each test runs.
    """
    import formaltask.validators.doc_guard_config as dgc

    dgc._config_cache = None
    yield
    dgc._config_cache = None


@pytest.fixture
def mock_review_gates(monkeypatch):
    """Mock check_completion to always allow.

    Use this fixture for tests that need to complete tasks without
    running actual review gate enforcement.
    """
    from formaltask.core.completion_check import CompletionCheck

    def mock_fn(_tid, _db):
        return CompletionCheck(allowed=True, phase="done", reason=None)

    monkeypatch.setattr("formaltask.core.completion_check.check_completion", mock_fn)


def make_valid_review_findings(findings: list = None, summary: str = "Test review summary") -> str:
    """Create valid JSON for task_reviews.findings column (database CHECK constraint).

    Creates JSON matching task_reviews.findings CHECK constraint requirements:
    - json_valid(findings) = 1
    - json_type(findings, '$.findings') = 'array'
    - json_extract(findings, '$.summary') IS NOT NULL
    - length(json_extract(findings, '$.summary')) > 0
    """
    return json.dumps({"findings": findings or [], "summary": summary})


def make_valid_review(
    approved: bool = True,
    findings: list = None,
    summary: str = "All checks passed",
    round_num: int = 1,
) -> dict:
    """Create review dict that passes CHECK constraint.

    Args:
        approved: Review approval status (default: True).
        findings: List of finding strings (default: empty list).
        summary: Summary string (default: "All checks passed").
        round_num: Review round number (default: 1).

    Returns:
        dict: Review dictionary with round, approved, and findings keys.
    """
    return {
        "round": round_num,
        "approved": approved,
        "findings": json.dumps({"findings": findings or [], "summary": summary}),
    }


def make_worker_state(**overrides) -> dict:
    """Factory for worker state dicts matching get_worker_state_dict() shape."""
    defaults = {
        "task_id": 1,
        "session_name": "task-1",
        "title": "Test Task",
        "pane_output": "",
        "health_state": "running",
        "is_stale": False,
        "source": "pane_scrape",
        "pr_number": None,
        "pr_status": "none",
        "worktree_path": None,
        "commits_ahead": 0,
        "started_at": None,
        "reviews_required": 0,
        "reviews_completed": 0,
        "tmux_session_exists": True,
        "pending_question": None,
        "finding_counts": {},
        "epic_name": "test-epic",
    }
    return {**defaults, **overrides}
