"""Tests for hooks/lib/task_context.py shared utility."""

import sqlite3

import pytest


@pytest.fixture
def task_db(tmp_path):
    """Database with tasks/acceptance_criteria tables."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY, title TEXT, description TEXT,
            epic_name TEXT, metadata TEXT, depends_on TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE acceptance_criteria (
            id INTEGER PRIMARY KEY, task_id INTEGER, text TEXT,
            checked INTEGER DEFAULT 0, command TEXT
        )
    """)
    conn.close()
    return db_path


class TestLoadTaskContext:
    """Tests for load_task_context() function."""

    def test_load_task_context_returns_none_when_db_missing(self, tmp_path):
        """load_task_context returns None when database file doesn't exist."""
        from formaltask.tasks.context import load_task_context

        db_path = tmp_path / "nonexistent.db"
        result = load_task_context(42, db_path)
        assert result is None

    def test_load_task_context_returns_none_when_task_not_found(self, task_db):
        """load_task_context returns None when task ID doesn't exist."""
        from formaltask.tasks.context import load_task_context

        result = load_task_context(999, task_db)
        assert result is None

    def test_load_task_context_returns_task_data(self, task_db):
        """load_task_context returns task data when task exists."""
        import json

        from formaltask.tasks.context import load_task_context

        metadata = json.dumps(
            {"artifact_type": "spec", "artifact_content": "## Requirements\n- Do stuff"}
        )
        conn = sqlite3.connect(str(task_db))
        conn.execute(
            """
            INSERT INTO tasks (id, title, description, epic_name, metadata, depends_on)
            VALUES (42, 'Fix auth bug', 'Fix the authentication issue', 'auth-epic', ?, '[1, 2]')
        """,
            (metadata,),
        )
        conn.commit()
        conn.close()

        result = load_task_context(42, task_db)

        assert result is not None
        assert result["title"] == "Fix auth bug"
        assert result["description"] == "Fix the authentication issue"
        assert result["epic_name"] == "auth-epic"
        assert result["artifact_type"] == "spec"
        assert result["artifact_content"] == "## Requirements\n- Do stuff"
        assert result["depends_on"] == "[1, 2]"

    def test_load_task_context_handles_null_metadata(self, task_db):
        """load_task_context handles NULL metadata gracefully."""
        from formaltask.tasks.context import load_task_context

        conn = sqlite3.connect(str(task_db))
        conn.execute("""
            INSERT INTO tasks (id, title, description, epic_name, metadata, depends_on)
            VALUES (42, 'Task', 'Desc', 'epic', NULL, '[]')
        """)
        conn.commit()
        conn.close()

        result = load_task_context(42, task_db)

        assert result is not None
        assert result["artifact_type"] == ""
        assert result["artifact_content"] == ""

    def test_load_task_context_handles_invalid_json_metadata(self, task_db):
        """load_task_context handles corrupt JSON metadata gracefully."""
        from formaltask.tasks.context import load_task_context

        conn = sqlite3.connect(str(task_db))
        conn.execute("""
            INSERT INTO tasks (id, title, description, epic_name, metadata, depends_on)
            VALUES (42, 'Task', 'Desc', 'epic', 'not valid json', '[]')
        """)
        conn.commit()
        conn.close()

        result = load_task_context(42, task_db)

        assert result is not None
        assert result["title"] == "Task"
        assert result["artifact_type"] == ""
        assert result["artifact_content"] == ""

    def test_load_task_context_returns_none_on_db_error(self, tmp_path):
        """load_task_context returns None on database errors."""
        from formaltask.tasks.context import load_task_context

        db_path = tmp_path / "test.db"
        # Create a file that's not a valid SQLite database
        db_path.write_text("not a database")

        result = load_task_context(42, db_path)
        assert result is None

    def test_load_task_context_extracts_non_goals_from_metadata(self, task_db):
        """load_task_context extracts non_goals list from task metadata."""
        import json

        from formaltask.tasks.context import load_task_context

        metadata = json.dumps(
            {
                "artifact_type": "spec",
                "artifact_content": "## Requirements",
                "non_goals": ["Do not refactor unrelated code", "Skip documentation updates"],
            }
        )
        conn = sqlite3.connect(str(task_db))
        conn.execute(
            """
            INSERT INTO tasks (id, title, description, epic_name, metadata, depends_on)
            VALUES (42, 'Task', 'Desc', 'epic', ?, '[]')
        """,
            (metadata,),
        )
        conn.commit()
        conn.close()

        result = load_task_context(42, task_db)

        assert result is not None
        assert "non_goals" in result
        assert result["non_goals"] == [
            "Do not refactor unrelated code",
            "Skip documentation updates",
        ]

    def test_load_task_context_returns_empty_list_when_non_goals_missing(self, task_db):
        """load_task_context returns empty list when non_goals not in metadata."""
        import json

        from formaltask.tasks.context import load_task_context

        metadata = json.dumps({"artifact_type": "spec", "artifact_content": "## Requirements"})
        conn = sqlite3.connect(str(task_db))
        conn.execute(
            """
            INSERT INTO tasks (id, title, description, epic_name, metadata, depends_on)
            VALUES (42, 'Task', 'Desc', 'epic', ?, '[]')
        """,
            (metadata,),
        )
        conn.commit()
        conn.close()

        result = load_task_context(42, task_db)

        assert result is not None
        assert result["non_goals"] == []

    def test_load_task_context_extracts_skills_from_metadata(self, task_db):
        """load_task_context extracts skills list from task metadata."""
        import json

        from formaltask.tasks.context import load_task_context

        metadata = json.dumps(
            {
                "artifact_type": "spec",
                "artifact_content": "## Requirements",
                "skills": ["error-debugger", "root-cause-tracing"],
            }
        )
        conn = sqlite3.connect(str(task_db))
        conn.execute(
            """
            INSERT INTO tasks (id, title, description, epic_name, metadata, depends_on)
            VALUES (42, 'Task', 'Desc', 'epic', ?, '[]')
        """,
            (metadata,),
        )
        conn.commit()
        conn.close()

        result = load_task_context(42, task_db)

        assert result is not None
        assert "skills" in result
        assert result["skills"] == ["error-debugger", "root-cause-tracing"]

    def test_load_task_context_returns_empty_list_when_skills_missing(self, task_db):
        """load_task_context returns empty list when skills not in metadata."""
        import json

        from formaltask.tasks.context import load_task_context

        metadata = json.dumps({"artifact_type": "spec", "artifact_content": "## Requirements"})
        conn = sqlite3.connect(str(task_db))
        conn.execute(
            """
            INSERT INTO tasks (id, title, description, epic_name, metadata, depends_on)
            VALUES (42, 'Task', 'Desc', 'epic', ?, '[]')
        """,
            (metadata,),
        )
        conn.commit()
        conn.close()

        result = load_task_context(42, task_db)

        assert result is not None
        assert result["skills"] == []


# ============ Task #2859: Runnable acceptance criteria tests ============


class TestLoadTaskContextRunnableAC:
    """Tests for load_task_context() returning acceptance criteria with commands."""

    def test_load_task_context_returns_criteria_with_command(self, task_db):
        """load_task_context returns acceptance_criteria as list[dict] with text+command.

        Task #2859: acceptance_criteria now includes command field for runnable AC.
        """
        import json

        from formaltask.tasks.context import load_task_context

        # Add command column to fixture (the fixture doesn't have it)
        conn = sqlite3.connect(str(task_db))
        try:
            conn.execute("ALTER TABLE acceptance_criteria ADD COLUMN command TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

        metadata = json.dumps({"artifact_type": "spec", "artifact_content": "## Spec"})
        conn.execute(
            """
            INSERT INTO tasks (id, title, description, epic_name, metadata, depends_on)
            VALUES (42, 'Task', 'Desc', 'epic', ?, '[]')
        """,
            (metadata,),
        )
        # Insert criteria with commands
        conn.execute(
            """INSERT INTO acceptance_criteria (task_id, text, command)
               VALUES (42, 'Text-only criterion', NULL)"""
        )
        conn.execute(
            """INSERT INTO acceptance_criteria (task_id, text, command)
               VALUES (42, 'Runnable criterion', 'pytest tests/')"""
        )
        conn.commit()
        conn.close()

        result = load_task_context(42, task_db)

        assert result is not None
        ac = result["acceptance_criteria"]
        # Now returns list[dict] instead of list[str]
        assert isinstance(ac, list)
        assert len(ac) == 2
        assert ac[0] == {"text": "Text-only criterion", "command": None}
        assert ac[1] == {"text": "Runnable criterion", "command": "pytest tests/"}
