"""Database fixtures for FormalTask tests (Task #1652).

Extracted from conftest.py to provide modular, focused fixture organization.
These fixtures provide isolated database instances for testing.

Fixtures provided:
- db_path: Function-scoped temporary database with schema loaded
- session_db: Session-scoped database for Hypothesis property tests
- session_db_with_task: Session-scoped database with pre-populated data
- db_with_epic_and_tasks: Database with test epic and 5 tasks
- minimal_schema_for_migration_testing: Minimal schema for migration tests
"""

import sqlite3
from pathlib import Path

import pytest

from tests.fixtures.paths import SCHEMA_FILE

# Task #2652: Schema now at formaltask/data/schema.sql, loaded via SCHEMA_FILE from paths.py


def _load_schema_for_tests(schema_file: Path) -> str:
    """Load schema SQL for tests.

    Schema no longer contains WAL pragma (handled by db_connection.py at runtime).

    Args:
        schema_file: Path to schema SQL file

    Returns:
        Schema SQL contents

    Raises:
        FileNotFoundError: If schema file doesn't exist (with clear message)
    """
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")
    with open(schema_file) as f:
        return f.read()


# ============================================================================
# Session-Scoped Fixtures for Hypothesis
# ============================================================================


@pytest.fixture(scope="session")
def session_db(tmp_path_factory):
    """Session-scoped test database for Hypothesis property tests.

    Uses tmp_path_factory (not tmp_path) because session fixtures cannot
    use function-scoped fixtures. Data accumulates across test runs within
    the session - tests should use assume() for preconditions.

    Returns:
        str: Path to temporary database file with schema loaded.
    """
    data_dir = tmp_path_factory.mktemp("data")
    db_file = data_dir / "test_formaltask.db"

    # Load schema
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_FILE}")

    schema_sql = _load_schema_for_tests(SCHEMA_FILE)

    with sqlite3.connect(db_file) as conn:
        # Execute schema - executescript auto-commits each statement
        conn.executescript(schema_sql)

        # Verify critical tables were created
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        required_tables = {"epics", "tasks", "commits", "acceptance_criteria"}
        missing = required_tables - tables
        if missing:
            raise RuntimeError(
                f"Schema loading failed - missing tables: {missing}. "
                f"Schema file: {SCHEMA_FILE}, Tables found: {tables}, "
                f"Schema SQL length: {len(schema_sql)}"
            )

        # Create migrations tracking table and mark all migrations as applied
        # This prevents re-running migrations that are already incorporated
        # into the base schema
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)

        # Mark Python migrations as applied (Task #2392: prevent spurious migration runs)
        # These migrations are already incorporated into the schema
        # Note: SQL migrations removed in Task #2654 - only Python migrations remain
        python_migration_names = [
            "024_fix_workers_pid_nullable",
            "025_add_worker_state_columns",
            "026_consolidate_reviews",
            "032_drop_pending_decisions",
            "add_blocked_question_to_tasks",
            "add_review_sha_and_round",
            "add_task_artifacts",
            "drop_unused_worker_columns",
            "drop_worker_columns",
            "fix_epic_status_completed_count",
            "migrate_planning_json_to_db",
            "migrate_worker_columns",
            "task_completion_state",
        ]
        for migration_name in python_migration_names:
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (name, applied_at) VALUES (?, datetime('now'))",
                (migration_name,),
            )
        conn.commit()  # Commit migrations tracking

    return str(db_file)


@pytest.fixture(scope="session")
def session_db_with_task(session_db):
    """Session-scoped database with pre-populated epic and task.

    Creates a single epic and task for Hypothesis property tests to use.
    Data persists across all tests in the session.

    Returns:
        str: Path to database with test data.
    """
    with sqlite3.connect(session_db) as conn:
        # Create epic for hypothesis tests
        conn.execute(
            "INSERT OR IGNORE INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("hypothesis-test-epic", "Epic for Hypothesis property tests", "2025-01-01T00:00:00Z"),
        )

        # Create a task
        conn.execute(
            """INSERT OR IGNORE INTO tasks
               (epic_name, title, description, status, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                "hypothesis-test-epic",
                "Hypothesis Test Task",
                "Task for property tests",
                "open",
                "2025-01-01T00:00:00Z",
            ),
        )

        conn.commit()

    return session_db


# ============================================================================
# Function-Scoped Database Fixtures
# ============================================================================


@pytest.fixture
def db_path(tmp_path):
    """Create temporary database with schema and mark all migrations as applied.

    Returns:
        str: Path to temporary database file with schema loaded.

    Usage:
        def test_something(db_path, repo):
            conn = sqlite3.connect(db_path)
            # ... test code ...

    Note:
        The base schema (formaltask/data/schema.sql) includes ALL migration columns.
        Migrations are marked as applied WITHOUT execution to prevent
        migration 001 from recreating tables with fewer columns.
        Tests inserting into task_reviews table must use make_valid_review_findings() from tests.conftest.
    """
    db_file = tmp_path / "test_formaltask.db"

    with sqlite3.connect(db_file) as conn:
        # Apply base schema (includes all migration columns)
        schema_sql = _load_schema_for_tests(SCHEMA_FILE)
        conn.executescript(schema_sql)

        # Create schema_migrations tracking table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)

        # Mark Python migrations as applied (they use custom names)
        # Note: SQL migrations removed in Task #2654 - only Python migrations remain
        python_migration_names = [
            "024_fix_workers_pid_nullable",
            "025_add_worker_state_columns",
            "026_consolidate_reviews",
            "032_drop_pending_decisions",
            "add_blocked_question_to_tasks",
            "add_reminder_count",
            "add_review_sha_and_round",
            "add_task_artifacts",
            "drop_unused_worker_columns",
            "drop_worker_columns",
            "fix_epic_status_completed_count",
            "migrate_planning_json_to_db",
            "migrate_worker_columns",
            "task_completion_state",
        ]
        for migration_name in python_migration_names:
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (name, applied_at) VALUES (?, datetime('now'))",
                (migration_name,),
            )

        # critique_findings table REMOVED (Task #2778) - never existed in production, no tests use it

        conn.commit()

    return str(db_file)


@pytest.fixture
def minimal_schema_for_migration_testing():
    """Minimal schema SQL that triggers migration execution.

    This schema lacks columns like review_status that the fresh schema detection
    uses to skip migrations. By omitting these columns, we force the database
    to run migrations, allowing tests to verify migration error handling.

    Returns:
        str: SQL schema string without migration-added columns.

    Usage:
        def test_migration_error(tmp_path, minimal_schema_for_migration_testing, monkeypatch):
            fake_project_root = tmp_path / "fake_project"
            schema_file = fake_project_root / "formaltask" / "data" / "schema.sql"
            schema_file.parent.mkdir(parents=True)
            schema_file.write_text(minimal_schema_for_migration_testing)
            # ... set up invalid migration and test error handling ...
    """
    return """
        CREATE TABLE IF NOT EXISTS epics (
            name TEXT PRIMARY KEY,
            description TEXT,
            created_at TEXT,
            archived_at TEXT,
            skip_review INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            epic_name TEXT,
            title TEXT,
            description TEXT,
            status TEXT DEFAULT 'open',
            position INTEGER,
            created_at TEXT,
            started_at TEXT,
            completed_at TEXT,
            depends_on TEXT DEFAULT '[]',
            is_parallel INTEGER DEFAULT 0,
            metadata TEXT
        );
        CREATE TABLE IF NOT EXISTS acceptance_criteria (
            id INTEGER PRIMARY KEY,
            task_id INTEGER,
            text TEXT,
            checked INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY,
            task_id INTEGER,
            round INTEGER,
            approved INTEGER,
            findings TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS commits (
            id INTEGER PRIMARY KEY,
            task_id INTEGER,
            commit_hash TEXT,
            commit_message TEXT
        );
        CREATE TABLE IF NOT EXISTS work_sessions (
            worktree_path TEXT PRIMARY KEY,
            current_task_id INTEGER
        );
        INSERT OR IGNORE INTO epics (name, description, created_at)
        VALUES ('master-adhoc', 'Unplanned work', datetime('now'));
    """


@pytest.fixture
def repo(db_path):
    """Test helper with db_path pre-bound for convenient data creation.

    Provides methods that delegate to standalone functions.

    Usage:
        def test_something(db_path, repo):
            repo.create_epic("test-epic", "Description")
            task_id = repo.create_task("test-epic", "Title", "Desc", ["criterion"])
            repo.link_commit(task_id, "abc123", "Message")
            repo.complete_task(task_id)
    """
    from types import SimpleNamespace

    from formaltask.db.connection import DatabaseConnection
    from formaltask.epics import create_epic as _create_epic
    from formaltask.tasks.crud import create_task as _create_task
    from formaltask.tasks.lifecycle import transition_task_status

    def create_epic(name, description, **kwargs):
        return _create_epic(db_path=db_path, name=name, description=description, **kwargs)

    def create_task(epic_name, title, description, criteria, **kwargs):
        return _create_task(
            db_path=db_path,
            epic_name=epic_name,
            title=title,
            description=description,
            criteria=criteria,
            **kwargs,
        )

    def link_commit(task_id, commit_hash, message):
        with DatabaseConnection(db_path) as conn:
            conn.cursor().execute(
                "INSERT OR IGNORE INTO commits (task_id, commit_hash, commit_message) VALUES (?, ?, ?)",
                (task_id, commit_hash, message),
            )
            conn.commit()

    def complete_task(task_id, review_data=None):
        # Note: review_data is ignored; just transitions status
        transition_task_status(db_path, task_id, "completed")

    return SimpleNamespace(
        create_epic=create_epic,
        create_task=create_task,
        link_commit=link_commit,
        complete_task=complete_task,
        db_path=db_path,
    )


@pytest.fixture
def db_with_epic_and_tasks(db_path):
    """Database with pre-populated epic and tasks for testing.

    Creates:
        - 1 epic: "test-epic"
        - 5 tasks with various states:
          * Task 1: open (position 1)
          * Task 2: open (position 2)
          * Task 3: in_progress (position 3)
          * Task 4: completed (position 4)
          * Task 5: blocked (position 5)

    Returns:
        str: Path to database with test data.

    Usage:
        def test_task_operations(db_with_epic_and_tasks):
            conn = sqlite3.connect(db_with_epic_and_tasks)
            # Test tasks are already present
    """
    with sqlite3.connect(db_path) as conn:
        # Create epic (no status column - status is computed from tasks)
        conn.execute(
            "INSERT INTO epics (name, description, created_at) VALUES (?, ?, ?)",
            ("test-epic", "Test epic for testing", "2025-01-01T00:00:00Z"),
        )

        # Create tasks with various states
        tasks = [
            (1, "test-epic", "Task 1", "open", 1),
            (2, "test-epic", "Task 2", "open", 2),
            (3, "test-epic", "Task 3", "in_progress", 3),
            (4, "test-epic", "Task 4", "completed", 4),
            (5, "test-epic", "Task 5", "blocked", 5),
        ]

        for task_id, epic, title, status, position in tasks:
            conn.execute(
                """INSERT INTO tasks
                   (id, epic_name, title, description, status, position, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (task_id, epic, title, "Description", status, position, "2025-01-01T00:00:00Z"),
            )

        conn.commit()

    return db_path
