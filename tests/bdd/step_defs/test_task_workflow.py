"""Step definitions for task workflow BDD tests."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from formaltask.epics import create_epic as _create_epic
from formaltask.tasks.crud import create_task as _create_task
from formaltask.tasks.crud import get_task as _get_task
from formaltask.tasks.lifecycle import transition_task_status

# Load scenarios from the feature file
scenarios("../features/task_workflow.feature")

# Note: bdd_db fixture is provided by hooks/tests/bdd/conftest.py


@pytest.fixture
def task_context():
    """Shared context for task tests."""
    return {}


@given("a clean FormalTask database")
def clean_database(bdd_db, task_context):
    """Set up a clean database."""
    task_context["db_path"] = bdd_db
    task_context["tasks"] = {}


@given(parsers.parse('an epic named "{name}" exists'))
def epic_exists_setup(task_context, name):
    """Create an epic as prerequisite."""
    _create_epic(db_path=task_context["db_path"], name=name, description="Pre-existing epic")


@when(parsers.parse('I create a task "{title}" in "{epic}"'))
def create_task(task_context, title, epic):
    """Create a task in an epic."""
    task_id = _create_task(
        db_path=task_context["db_path"],
        epic_name=epic,
        title=title,
        description=f"Description for {title}",
        criteria=["Acceptance criterion"],
    )
    task_context["last_task_id"] = task_id
    task_context["tasks"][title] = task_id


@then(parsers.parse('the task "{title}" should exist in "{epic}"'))
def verify_task_exists(task_context, title, epic):
    """Verify task exists in the specified epic."""
    task_id = task_context["tasks"].get(title)
    assert task_id is not None, f"Task '{title}' not in context"
    task = _get_task(db_path=task_context["db_path"], task_id=task_id)
    assert task is not None, f"Task '{title}' not found in database"
    assert task["epic_name"] == epic, f"Task '{title}' in wrong epic: {task['epic_name']}"


@given(parsers.parse('a task "{title}" exists in "{epic}"'))
def task_exists_setup(task_context, title, epic):
    """Create a task as prerequisite."""
    task_id = _create_task(
        db_path=task_context["db_path"],
        epic_name=epic,
        title=title,
        description=f"Description for {title}",
        criteria=["Acceptance criterion"],
    )
    task_context["tasks"][title] = task_id


@given(parsers.parse('a started task "{title}" exists in "{epic}"'))
def started_task_exists_setup(task_context, title, epic):
    """Create a started task as prerequisite."""
    task_id = _create_task(
        db_path=task_context["db_path"],
        epic_name=epic,
        title=title,
        description=f"Description for {title}",
        criteria=["Acceptance criterion"],
    )
    transition_task_status(task_context["db_path"], task_id, "in_progress")
    task_context["tasks"][title] = task_id


@when(parsers.parse('I start the task "{title}"'))
def start_task(task_context, title):
    """Start a task."""
    task_id = task_context["tasks"][title]
    transition_task_status(task_context["db_path"], task_id, "in_progress")


@when(parsers.parse('I complete the task "{title}"'))
def complete_task(task_context, title):
    """Complete a task."""
    task_id = task_context["tasks"][title]
    transition_task_status(task_context["db_path"], task_id, "completed")


@then(parsers.parse('the task "{title}" should have status "{status}"'))
def verify_task_status(task_context, title, status):
    """Verify task has the expected status."""
    task_id = task_context["tasks"][title]
    task = _get_task(db_path=task_context["db_path"], task_id=task_id)
    assert task["status"] == status, f"Expected status '{status}', got '{task['status']}'"


@when(parsers.parse('I retrieve task "{title}" by ID'))
def retrieve_task_by_id(task_context, title):
    """Retrieve a task by its ID."""
    task_id = task_context["tasks"][title]
    task_context["retrieved_task"] = _get_task(db_path=task_context["db_path"], task_id=task_id)


@then(parsers.parse('the task should have title "{title}"'))
def verify_task_title(task_context, title):
    """Verify retrieved task has expected title."""
    assert task_context["retrieved_task"]["title"] == title


@then(parsers.parse('the task should have epic "{epic}"'))
def verify_task_epic(task_context, epic):
    """Verify retrieved task belongs to expected epic."""
    assert task_context["retrieved_task"]["epic_name"] == epic


@then(parsers.parse("the task should have position {position:d}"))
def verify_task_position(task_context, position):
    """Verify retrieved task has expected position."""
    actual = task_context["retrieved_task"]["position"]
    assert actual == position, f"Expected position {position}, got {actual}"
