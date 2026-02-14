"""Step definitions for epic workflow BDD tests."""

import sqlite3
from datetime import datetime

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from formaltask.epics import create_epic as _create_epic
from formaltask.epics import get_epic_status as _get_epic_status
from formaltask.tasks.crud import create_task as _create_task

# Load scenarios from the feature file
scenarios("../features/epic_workflow.feature")

# Note: bdd_db fixture is provided by hooks/tests/bdd/conftest.py


@pytest.fixture
def epic_context():
    """Shared context for epic tests."""
    return {}


@given("a clean FormalTask database")
def clean_database(bdd_db, epic_context):
    """Set up a clean database."""
    epic_context["db_path"] = bdd_db


@when(parsers.parse('I create an epic named "{name}"'))
def create_epic(epic_context, name):
    """Create an epic with the given name."""
    _create_epic(db_path=epic_context["db_path"], name=name, description="Test description")


@then(parsers.parse('the epic "{name}" should exist'))
def epic_exists(epic_context, name):
    """Verify epic exists in database."""
    with sqlite3.connect(epic_context["db_path"]) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM epics WHERE name = ?", (name,))
        row = cursor.fetchone()
    assert row is not None, f"Epic '{name}' not found"
    assert row[0] == name


@given(parsers.parse('an epic named "{name}" exists'))
def epic_exists_setup(epic_context, name):
    """Create an epic as prerequisite."""
    _create_epic(db_path=epic_context["db_path"], name=name, description="Pre-existing epic")


@when(parsers.parse('I try to create an epic named "{name}"'))
def try_create_epic(epic_context, name):
    """Attempt to create epic, capturing any error."""
    try:
        _create_epic(db_path=epic_context["db_path"], name=name, description="Duplicate attempt")
        epic_context["error"] = None
    except Exception as e:
        epic_context["error"] = e


@then("I should get a duplicate error")
def verify_duplicate_error(epic_context):
    """Verify that a duplicate error was raised."""
    assert epic_context.get("error") is not None, "Expected error but none occurred"
    assert "UNIQUE constraint" in str(epic_context["error"]) or "already exists" in str(
        epic_context["error"]
    )


@when("I list all epics")
def list_all_epics(epic_context):
    """List all epics by querying database (excluding system epics)."""
    with sqlite3.connect(epic_context["db_path"]) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM epics WHERE name != 'master-adhoc'")
        epic_context["epics"] = cursor.fetchall()


@then(parsers.parse("I should see {count:d} epics in the result"))
def verify_epic_count(epic_context, count):
    """Verify the number of epics returned."""
    actual = len(epic_context["epics"])
    assert actual == count, f"Expected {count} epics, got {actual}"


@when(parsers.parse('I get the status of "{name}"'))
def get_epic_status(epic_context, name):
    """Get the status of an epic."""
    epic_context["status"] = _get_epic_status(db_path=epic_context["db_path"], name=name)


@then(parsers.parse("the status should show {count:d} total tasks"))
def verify_total_tasks(epic_context, count):
    """Verify total task count in status."""
    actual = epic_context["status"]["total_tasks"]
    assert actual == count, f"Expected {count} total tasks, got {actual}"


@given(parsers.parse('a task "{title}" in "{epic}" with status "{status}"'))
def create_task_with_status(epic_context, title, epic, status):
    """Create a task with a specific status."""
    task_id = _create_task(
        db_path=epic_context["db_path"],
        epic_name=epic,
        title=title,
        description=f"Test task: {title}",
        criteria=["Test criterion"],
    )
    # Update status and timestamps based on status
    with sqlite3.connect(epic_context["db_path"]) as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        if status == "completed":
            cursor.execute(
                "UPDATE tasks SET status = ?, started_at = ?, completed_at = ? WHERE id = ?",
                (status, now, now, task_id),
            )
        elif status == "in_progress":
            cursor.execute(
                "UPDATE tasks SET status = ?, started_at = ? WHERE id = ?", (status, now, task_id)
            )
        else:
            cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
        conn.commit()


@then(parsers.parse("the status should show {count:d} completed tasks"))
def verify_completed_tasks(epic_context, count):
    """Verify completed task count in status."""
    actual = epic_context["status"]["completed"]
    assert actual == count, f"Expected {count} completed tasks, got {actual}"
