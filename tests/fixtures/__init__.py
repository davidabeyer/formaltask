"""Pytest fixtures directory for modular test fixtures (Task #1651).

This module registers fixture modules via pytest_plugins for automatic discovery.
Add fixture modules to the list as they are extracted from conftest.py.

Usage:
    pytest_plugins = [
        "tests.fixtures.database",
        "tests.fixtures.mocks",
    ]
"""

# Fixture modules to be loaded by pytest.
# Add modules as fixtures are extracted from conftest.py.
pytest_plugins: list[str] = [
    "tests.fixtures.database",  # db_path, session_db, db_with_epic_and_tasks
    "tests.fixtures.mocks",  # mock_gh_cli, skip_sqlite
    # Task #1863: accumulated_context fixture removed
    "tests.fixtures.worktree",  # session_dir, worktree_root
]

# Re-export path constants for convenient import (Task #2127)
# Note: PRE_COMPACT_DIR removed (pre-compact archived)
# Note: MIGRATIONS_DIR removed (Task #2654 - SQL migrations deleted)
from tests.fixtures.paths import (
    CLI_DIR,
    FIXTURES_DIR,
    GOLDEN_FIXTURES_DIR,
    HOOKS_DIR,
    LIB_DIR,
    PROJECT_ROOT,
    SCHEMA_FILE,
    SESSION_END_DIR,
    SESSION_START_DIR,
    TESTS_DIR,
    TRANSCRIPT_FIXTURES_DIR,
    UNIT_TESTS_DIR,
    USER_PROMPT_DIR,
)

__all__ = [
    "CLI_DIR",
    "FIXTURES_DIR",
    "GOLDEN_FIXTURES_DIR",
    "HOOKS_DIR",
    "LIB_DIR",
    "PROJECT_ROOT",
    "SCHEMA_FILE",
    "SESSION_END_DIR",
    "SESSION_START_DIR",
    "TESTS_DIR",
    "TRANSCRIPT_FIXTURES_DIR",
    "UNIT_TESTS_DIR",
    "USER_PROMPT_DIR",
]
