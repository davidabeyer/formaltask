"""Test epic_create command."""

import sqlite3

import pytest

from formaltask.db.connection import DatabaseConnection


def test_epic_create_success(db_path):
    """
    RED: Test creating a new epic successfully.

    Should:
    - Insert epic into database
    - Set created_at timestamp
    - Return epic name
    """
    from formaltask.cli.commands.epic_create import epic_create

    # When: Creating an epic
    result = epic_create(
        epic_name="test-epic",
        description="Test epic description",
        db_path=db_path,
    )

    # Then: Should return dict with epic_name and created flag
    assert result == {"epic_name": "test-epic", "created": True}

    # Verify in database
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, description, skip_review FROM epics WHERE name = ?", ("test-epic",)
        )
        result = cursor.fetchone()
        assert result is not None, "Epic 'test-epic' not found"
        assert tuple(result) == ("test-epic", "Test epic description", False)


def test_epic_create_with_skip_review(db_path):
    """
    RED: Test creating an epic with skip_review=True.
    """
    from formaltask.cli.commands.epic_create import epic_create

    # When: Creating an epic with skip_review
    result = epic_create(
        epic_name="no-review-epic",
        description="Epic without review",
        db_path=db_path,
        skip_review=True,
    )

    # Then: skip_review should be True in database
    assert result == {"epic_name": "no-review-epic", "created": True}

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT skip_review FROM epics WHERE name = ?", ("no-review-epic",))
        result = cursor.fetchone()
        # DatabaseConnection sets row_factory=sqlite3.Row, so convert to tuple
        assert tuple(result) == (True,)


def test_epic_create_duplicate_name_fails(db_path):
    """
    RED: Test that creating an epic with duplicate name fails.
    """
    from formaltask.cli.commands.epic_create import epic_create

    # Given: Epic already exists
    epic_create(
        epic_name="existing-epic",
        description="First epic",
        db_path=db_path,
    )

    # When/Then: Trying to create epic with same name should raise IntegrityError
    with pytest.raises(sqlite3.IntegrityError):
        epic_create(
            epic_name="existing-epic",
            description="Duplicate epic",
            db_path=db_path,
        )
