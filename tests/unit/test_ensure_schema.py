"""Tests for ensure_schema.py migration consolidation (Task #2684).

TDD: RED phase - test ensure_schema before implementation.

Tests that ensure_schema:
1. Module exists and has ENSURE_COLUMNS and migrate()
2. Adds missing columns idempotently
3. Skips columns that already exist
4. Works with fresh schema (all columns exist)
"""

import sqlite3


def test_ensure_schema_adds_missing_columns(tmp_path):
    """migrate() should add missing columns to tables."""
    from formaltask.db.migrations.ensure_schema import migrate

    db_path = tmp_path / "test.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Create minimal tables without the columns that ensure_schema adds
        cursor.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE epics (
                name TEXT PRIMARY KEY
            )
        """)
        cursor.execute("""
            CREATE TABLE task_reviews (
                id INTEGER PRIMARY KEY,
                task_id INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE planning_state (
                project_name TEXT PRIMARY KEY
            )
        """)
        cursor.execute("""
            CREATE TABLE schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)
        conn.commit()

    result = migrate(str(db_path))

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Check tasks table columns
        cursor.execute("PRAGMA table_info(tasks)")
        task_columns = {row[1] for row in cursor.fetchall()}

        # Check epics table columns
        cursor.execute("PRAGMA table_info(epics)")
        epic_columns = {row[1] for row in cursor.fetchall()}

        # Check task_reviews table columns
        cursor.execute("PRAGMA table_info(task_reviews)")
        review_columns = {row[1] for row in cursor.fetchall()}

        # Check planning_state table columns
        cursor.execute("PRAGMA table_info(planning_state)")
        planning_columns = {row[1] for row in cursor.fetchall()}

    # Verify expected columns from ENSURE_COLUMNS were added
    assert "blocked_question" in task_columns
    assert "completion_evidence" in task_columns
    assert "defer_reason" in task_columns
    assert "cancel_reason" in task_columns
    assert "cancelled_at" in task_columns
    assert "session_id" in task_columns
    assert "review_round" in task_columns
    assert "pr_url" in task_columns
    assert "artifact_type" in task_columns

    assert "feature_branch" in epic_columns
    assert "reviewed_at" in epic_columns

    assert "round" in review_columns

    assert "plan_file_path" in planning_columns

    assert result is True


def test_ensure_schema_idempotent(tmp_path):
    """Running migrate() twice should not error (idempotent)."""
    from formaltask.db.migrations.ensure_schema import migrate

    db_path = tmp_path / "test.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE epics (
                name TEXT PRIMARY KEY
            )
        """)
        cursor.execute("""
            CREATE TABLE task_reviews (
                id INTEGER PRIMARY KEY,
                task_id INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE planning_state (
                project_name TEXT PRIMARY KEY
            )
        """)
        cursor.execute("""
            CREATE TABLE schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)
        conn.commit()

    result1 = migrate(str(db_path))
    result2 = migrate(str(db_path))

    assert result1 is True, "First run should apply migration"
    assert result2 is False, "Second run should skip (columns exist)"


def test_ensure_schema_skips_existing_columns(tmp_path):
    """migrate() should skip tables that already have the columns."""
    from formaltask.db.migrations.ensure_schema import migrate

    db_path = tmp_path / "test.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Create tables WITH the columns (like fresh schema.sql)
        cursor.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                blocked_question TEXT,
                completion_evidence TEXT,
                defer_reason TEXT,
                cancel_reason TEXT,
                cancelled_at TEXT,
                session_id TEXT,
                review_round INTEGER,
                pr_url TEXT,
                artifact_type TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE epics (
                name TEXT PRIMARY KEY,
                feature_branch TEXT,
                reviewed_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE task_reviews (
                id INTEGER PRIMARY KEY,
                task_id INTEGER,
                round INTEGER DEFAULT 1
            )
        """)
        cursor.execute("""
            CREATE TABLE planning_state (
                project_name TEXT PRIMARY KEY,
                plan_file_path TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)
        conn.commit()

    result = migrate(str(db_path))

    # No columns were added, so should return False
    assert result is False, "Should skip when all columns exist"


def test_ensure_schema_handles_missing_table(tmp_path):
    """migrate() should gracefully handle missing tables."""
    from formaltask.db.migrations.ensure_schema import migrate

    db_path = tmp_path / "test.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Only create tasks table, not others
        cursor.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)
        conn.commit()

    # Should not raise, just skip missing tables
    result = migrate(str(db_path))

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(tasks)")
        task_columns = {row[1] for row in cursor.fetchall()}

    # Tasks table columns should be added
    assert "blocked_question" in task_columns
    assert result is True
