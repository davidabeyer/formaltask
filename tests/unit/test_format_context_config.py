"""Tests for format_context config passing (Task #2821).

Verifies that format_context passes CompletionConfig to WorkerInstructionBuilder.
"""

import sqlite3
from pathlib import Path


def _create_test_db(db_path: Path) -> None:
    """Create test database with tasks and acceptance_criteria tables."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                epic_name TEXT,
                metadata TEXT,
                depends_on TEXT,
                status TEXT DEFAULT 'open',
                artifact_content TEXT,
                artifact_type TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE acceptance_criteria (
                id INTEGER PRIMARY KEY,
                task_id INTEGER,
                text TEXT
            )
        """)
        conn.commit()


class TestFormatContextUsesConfig:
    """Tests for format_context using CompletionConfig (Task #2821)."""

    def test_format_context_uses_config_required_reviews(self, tmp_path):
        """format_context should use config.required_reviews from task metadata."""
        import json

        from hooks.session_start.task_context_loader import format_context

        task_id = 42
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)

        # Insert task with custom required_reviews in metadata
        metadata = json.dumps({"required_reviews": ["security", "acceptance"]})
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO tasks (id, title, description, epic_name, metadata)
                   VALUES (?, ?, ?, ?, ?)""",
                (task_id, "Test Task", "Test description", "test-epic", metadata),
            )
            conn.commit()

        task_context = {
            "id": task_id,
            "title": "Test Task",
            "metadata": metadata,
        }

        # Call format_context with db_path
        result = format_context(task_context, db_path=db_path)

        # Should use metadata required_reviews, not default code-quality
        assert "security, acceptance" in result
        # Default should NOT appear since metadata overrides it
        assert "Required review types: code-quality" not in result

    def test_format_context_defaults_without_db_path(self):
        """format_context without db_path should not include reviews section."""
        from hooks.session_start.task_context_loader import format_context

        task_context = {
            "id": 42,
            "title": "Test Task",
        }

        # Call format_context without db_path (no config available)
        result = format_context(task_context)

        # Should NOT include review section when no config is available
        # (Task #2821: no hardcoded fallback - callers must provide config)
        assert "### Run Required Reviews" not in result
