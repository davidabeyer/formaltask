"""Tests for inject_blocked_context() in task_context_loader.py.

Task #2147: Inject blocked conversation context when resuming a worker.
Task #2388: Blocking state now lives on tasks table (tasks.blocked_question).
The blocked_summary concept was removed; only blocked_question remains.
"""

import sqlite3
from pathlib import Path


def _create_test_db(db_path: Path) -> None:
    """Create test database with tasks table schema."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'open',
                blocked_question TEXT
            )
        """)
        conn.commit()


def test_inject_blocked_context_returns_question_when_exists(tmp_path):
    """inject_blocked_context() returns formatted pending question when it exists."""
    from hooks.session_start.task_context_loader import inject_blocked_context

    db_path = tmp_path / "test.db"
    _create_test_db(db_path)
    task_id = 42

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tasks (id, title, blocked_question)
            VALUES (?, 'Test Task', 'What should I do next?')
            """,
            (task_id,),
        )
        conn.commit()

    result = inject_blocked_context(task_id, db_path)

    assert "PENDING QUESTION:" in result
    assert "What should I do next?" in result


def test_inject_blocked_context_returns_empty_when_null(tmp_path):
    """inject_blocked_context() returns empty string when blocked_question is NULL."""
    from hooks.session_start.task_context_loader import inject_blocked_context

    db_path = tmp_path / "test.db"
    _create_test_db(db_path)
    task_id = 200

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tasks (id, title, blocked_question)
            VALUES (?, 'Test Task', NULL)
            """,
            (task_id,),
        )
        conn.commit()

    result = inject_blocked_context(task_id, db_path)

    assert result == "", "Should return empty string when blocked_question is NULL"


def test_inject_blocked_context_returns_empty_when_no_task(tmp_path):
    """inject_blocked_context() returns empty string when task doesn't exist."""
    from hooks.session_start.task_context_loader import inject_blocked_context

    db_path = tmp_path / "test.db"
    _create_test_db(db_path)
    task_id = 999  # Non-existent task

    result = inject_blocked_context(task_id, db_path)

    assert result == "", "Should return empty string when task doesn't exist"


def test_inject_blocked_context_empty_string_treated_as_null(tmp_path):
    """Empty string blocked_question should be treated as NULL (no injection)."""
    from hooks.session_start.task_context_loader import inject_blocked_context

    db_path = tmp_path / "test.db"
    _create_test_db(db_path)
    task_id = 500

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tasks (id, title, blocked_question)
            VALUES (?, 'Test Task', '')
            """,
            (task_id,),
        )
        conn.commit()

    result = inject_blocked_context(task_id, db_path)

    assert result == "", "Empty string blocked_question should return empty string"


def test_main_includes_blocked_context_in_output(tmp_path, monkeypatch, capsys):
    """main() should include blocked context in additionalContext output.

    Integration test: when a task has blocked_question, main() should call
    inject_blocked_context() and include the result in the formatted output.
    """
    import json

    from hooks.session_start import task_context_loader

    task_id = 700

    # Set up worktree structure
    task_dir = tmp_path / ".task"
    task_dir.mkdir()
    (task_dir / "id").write_text(str(task_id))
    (task_dir / "main_repo").write_text(str(tmp_path))

    # Set up database
    db_dir = tmp_path / ".claude"
    db_dir.mkdir()
    db_path = db_dir / "formaltask.db"

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # Create tasks table with blocked_question
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
                artifact_type TEXT,
                blocked_question TEXT
            )
        """)
        cursor.execute(
            """INSERT INTO tasks (id, title, description, epic_name, blocked_question)
               VALUES (?, ?, ?, ?, ?)""",
            (
                task_id,
                "Test Task",
                "Test description",
                "test-epic",
                "How should I handle edge case Y?",
            ),
        )
        # Create acceptance_criteria table (required by load_task_context)
        cursor.execute("""
            CREATE TABLE acceptance_criteria (
                id INTEGER PRIMARY KEY,
                task_id INTEGER,
                text TEXT,
                command TEXT
            )
        """)
        conn.commit()

    # Mock cwd to point to our temp worktree
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    # Act
    task_context_loader.main()

    # Assert
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    additional_context = output["hookSpecificOutput"]["additionalContext"]

    # Blocked context should be in the output
    assert "PENDING QUESTION:" in additional_context
    assert "How should I handle edge case Y?" in additional_context
