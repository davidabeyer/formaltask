"""Centralized path constants for test fixtures (Task #2127).

All test files should import path constants from this module instead of
using Path(__file__) directly. This ensures consistent path resolution
and makes tests more maintainable.

Usage:
    from tests.fixtures.paths import PROJECT_ROOT, HOOKS_DIR
    from tests.fixtures.paths import get_schema_sql  # Preferred for schema loading
"""

from pathlib import Path

# Calculate paths relative to this file location
# fixtures/paths.py -> tests/ -> project_root/
_THIS_FILE = Path(__file__).resolve()
FIXTURES_DIR = _THIS_FILE.parent
TESTS_DIR = FIXTURES_DIR.parent
PROJECT_ROOT = TESTS_DIR.parent
HOOKS_DIR = PROJECT_ROOT / "hooks"

# Unit tests directory
UNIT_TESTS_DIR = TESTS_DIR / "unit"

# Hooks subdirectories
LIB_DIR = HOOKS_DIR / "lib"
CLI_DIR = HOOKS_DIR / "cli"
SESSION_END_DIR = HOOKS_DIR / "session_end"
SESSION_START_DIR = HOOKS_DIR / "session_start"  # register_active_session archived
USER_PROMPT_DIR = HOOKS_DIR / "user-prompt"
# Note: PRE_COMPACT_DIR removed - hooks/pre-compact/ archived

# Schema path (Task #2652: moved to formaltask/data/, Task #2654: SQL migrations removed)
SCHEMA_FILE = PROJECT_ROOT / "formaltask" / "data" / "schema.sql"

# Migrations directory (Task #2654: SQL migrations removed, kept for backwards compat)
# Tests check .exists() before iterating, so this path being absent is fine
MIGRATIONS_DIR = PROJECT_ROOT / "formaltask" / "data" / "migrations"

# Commonly used test fixture paths
TRANSCRIPT_FIXTURES_DIR = FIXTURES_DIR / "transcripts"
GOLDEN_FIXTURES_DIR = FIXTURES_DIR / "golden"
