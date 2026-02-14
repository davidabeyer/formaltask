"""Database schema initialization and migrations - standalone functions.

Extracted from EpicRepository (Task #1937), refactored to antirez-style
functions (Task #2627).
"""

import importlib
import logging
import sqlite3

# nosemgrep: python.lang.compatibility.python37.python37-compatibility-importlib2
from importlib.resources import files
from pathlib import Path

from formaltask.db.connection import DatabaseConnection
from formaltask.paths import get_project_root

__all__: list[str] = ["ensure_schema_initialized", "get_schema_sql"]

logger = logging.getLogger(__name__)

# Files to skip when discovering Python migrations
SKIP_MIGRATION_FILES = {"__init__.py", "helpers.py"}


def get_schema_sql() -> str:
    """Get schema SQL content via importlib.resources (Task #2652).

    Uses packaged formaltask/data/schema.sql instead of file system path.
    This allows pip-installed packages to work without PROJECT_ROOT.

    Returns:
        Schema SQL content as string
    """
    schema_resource = files("formaltask.data").joinpath("schema.sql")
    return schema_resource.read_text()


def ensure_schema_initialized(db_path: str) -> None:
    """Ensure database exists and schema is initialized.

    Idempotent operation that:
    1. Creates directory if missing
    2. Creates empty database file if missing
    3. Initializes schema if tables don't exist (uses formaltask/data/schema.sql)
    4. Runs Python migrations (formaltask/db/migrations/)
    5. Creates master-adhoc epic for hotfixes

    Note: SQL migrations (.claude/migrations/) deleted in Task #2654.
    Packaged schema.sql is the single source of truth for fresh databases.

    Args:
        db_path: Path to SQLite database file
    """
    db_path = str(db_path)
    db_file = Path(db_path)

    # Create directory if needed
    db_file.parent.mkdir(parents=True, exist_ok=True)

    # Create empty file if doesn't exist
    if not db_file.exists():
        db_file.touch()

    # Check if schema exists
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='epics'")

        if not cursor.fetchone():
            # Schema doesn't exist, initialize from packaged schema (Task #2652)
            try:
                schema_sql = get_schema_sql()
                cursor.executescript(schema_sql)
                logger.info(f"Initialized database schema at {db_path}")
            except Exception as e:
                logger.error(f"Failed to initialize schema: {e}")
                raise

    # Run Python migrations (SQL migrations removed in Task #2654)
    _run_python_migrations(db_path)


def _run_python_migrations(db_path: str) -> None:
    """Run pending Python migrations from formaltask/db/migrations/.

    Discovers .py files in the migrations directory and calls their
    migrate(db_path) function. Skips files in SKIP_MIGRATION_FILES.
    Each migration is responsible for its own idempotency checking
    via column_exists() or migration_applied() helpers.

    Migrations always run regardless of database age - idempotency checks
    make this safe. This ensures packaged schema.sql and Python migrations stay
    in sync as the single source of truth.

    Note: Unlike get_schema_sql() which uses importlib.resources, this function
    requires filesystem access via get_project_root(). Python migrations won't
    run in pip-installed packages without the source tree. This is acceptable
    because migrations are only needed during development; pip-installed packages
    use the fully-migrated schema.sql.

    Raises:
        sqlite3.Error: If a migration fails during database operations.
        ImportError: If a migration module cannot be imported.
        AttributeError: If migrate() call fails due to module issues.
    """
    # Lazy-load project root to avoid import-time crash (Task #2652)
    project_root = get_project_root()
    py_migrations_dir = project_root / "formaltask" / "db" / "migrations"
    if not py_migrations_dir.exists():
        logger.debug(f"Python migrations directory not found: {py_migrations_dir}")
        return

    for migration_file in sorted(py_migrations_dir.glob("*.py")):
        if migration_file.name in SKIP_MIGRATION_FILES:
            continue

        module_name = f"formaltask.db.migrations.{migration_file.stem}"

        try:
            # Safe: module_name uses hardcoded prefix + file stems from controlled migrations/ directory
            # nosemgrep: python.lang.security.audit.non-literal-import.non-literal-import
            module = importlib.import_module(module_name)

            if not hasattr(module, "migrate"):
                logger.debug(f"Skipping {migration_file.name}: no migrate() function")
                continue

            result = module.migrate(db_path)

            if result:
                logger.info(f"Applied Python migration: {migration_file.name}")
            else:
                logger.debug(f"Python migration already applied: {migration_file.name}")

        except (sqlite3.Error, ImportError, AttributeError) as e:
            logger.error(f"Python migration {migration_file.name} failed: {e}", exc_info=True)
            raise
