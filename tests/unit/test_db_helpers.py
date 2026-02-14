"""Tests for database helper utilities.

TDD Red phase: Tests written before implementation.
"""

import sqlite3

import pytest

from formaltask.exceptions import TaskNotFoundError


class TestEnsureTaskExists:
    """Tests for ensure_task_exists helper function."""

    @pytest.fixture
    def db_with_task(self):
        """Create in-memory database with a test task."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT, status TEXT)")
        cursor.execute("INSERT INTO tasks (id, title, status) VALUES (1, 'Test Task', 'open')")
        conn.commit()
        return conn

    def test_ensure_task_exists_returns_dict(self, db_with_task):
        """Test that valid task returns a dictionary with task data."""
        from formaltask.db.helpers import ensure_task_exists

        cursor = db_with_task.cursor()
        result = ensure_task_exists(cursor, 1)

        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["title"] == "Test Task"
        assert result["status"] == "open"

    def test_ensure_task_exists_raises_not_found(self, db_with_task):
        """Test that invalid task ID raises TaskNotFoundError."""
        from formaltask.db.helpers import ensure_task_exists

        cursor = db_with_task.cursor()

        with pytest.raises(TaskNotFoundError) as exc_info:
            ensure_task_exists(cursor, 999)

        assert exc_info.value.task_id == 999


class TestParseDependsOn:
    """Tests for parse_depends_on helper function."""

    def test_parse_depends_on_valid_json_list(self):
        """Parse valid JSON array returns list of integers."""
        from formaltask.db.helpers import parse_depends_on

        result = parse_depends_on("[1, 2, 3]")

        assert result == [1, 2, 3]

    def test_parse_depends_on_empty_json_array(self):
        """Parse empty JSON array returns empty list."""
        from formaltask.db.helpers import parse_depends_on

        result = parse_depends_on("[]")

        assert result == []

    def test_parse_depends_on_none_returns_empty(self):
        """None input returns empty list."""
        from formaltask.db.helpers import parse_depends_on

        result = parse_depends_on(None)

        assert result == []

    def test_parse_depends_on_empty_string_returns_empty(self):
        """Empty string returns empty list."""
        from formaltask.db.helpers import parse_depends_on

        result = parse_depends_on("")

        assert result == []

    def test_parse_depends_on_invalid_json_returns_empty(self):
        """Invalid JSON returns empty list (graceful degradation)."""
        from formaltask.db.helpers import parse_depends_on

        result = parse_depends_on("not valid json")

        assert result == []

    @pytest.mark.parametrize(
        "json_input,desc",
        [
            ('{"key": "value"}', "object"),
            ('"just a string"', "string"),
            ("42", "number"),
        ],
    )
    def test_parse_depends_on_non_list_json_returns_empty(self, json_input, desc):
        """Valid JSON that is not a list returns empty list."""
        from formaltask.db.helpers import parse_depends_on

        result = parse_depends_on(json_input)

        assert result == [], f"Expected [] for JSON {desc}"

    def test_parse_depends_on_single_element(self):
        """Single element array parses correctly."""
        from formaltask.db.helpers import parse_depends_on

        result = parse_depends_on("[42]")

        assert result == [42]

    def test_parse_depends_on_whitespace_preserved(self):
        """JSON with whitespace parses correctly."""
        from formaltask.db.helpers import parse_depends_on

        result = parse_depends_on("[ 1 , 2 , 3 ]")

        assert result == [1, 2, 3]

    def test_parse_depends_on_mixed_types_filters_to_int(self):
        """Mixed type array returns only integers for type safety."""
        from formaltask.db.helpers import parse_depends_on

        result = parse_depends_on('[1, "str", 2, null, 3, 1.5]')

        assert result == [1, 2, 3]
