"""Unit tests for task operations (Task #1658, #2711).

Tests task CRUD, lifecycle, and parallel safety operations.
Task #2711: TaskOperations inlined - tests use standalone functions.
"""

import pytest


def test_create_task_returns_id(db_path, repo):
    """P0: create_task returns int task ID."""
    repo.create_epic("test-epic", "A test epic")

    task_id = repo.create_task(
        epic_name="test-epic",
        title="Test Task",
        description="Task description",
        criteria=["Criterion 1", "Criterion 2"],
    )

    assert isinstance(task_id, int)
    assert task_id > 0


def test_create_task_unknown_epic_raises(db_path, repo):
    """P0: create_task raises EpicNotFoundError for unknown epic."""
    from formaltask.exceptions import EpicNotFoundError

    with pytest.raises(EpicNotFoundError) as exc_info:
        repo.create_task(
            epic_name="nonexistent-epic",
            title="Test Task",
            description="Task description",
            criteria=["Criterion 1"],
        )

    assert exc_info.value.epic_name == "nonexistent-epic"


def test_get_task_returns_dict(db_path, repo):
    """P0: get_task returns task dict with expected fields."""
    from formaltask.tasks.crud import get_task

    repo.create_epic("test-epic", "A test epic")

    task_id = repo.create_task(
        epic_name="test-epic",
        title="Test Task",
        description="Task description",
        criteria=["Criterion 1"],
    )

    task = get_task(db_path, task_id)

    assert task is not None
    assert task["id"] == task_id
    assert task["title"] == "Test Task"
    assert task["description"] == "Task description"
    assert task["status"] == "open"
    assert task["epic_name"] == "test-epic"


def test_get_tasks_returns_list(db_path, repo):
    """P0: get_tasks returns list of tasks for epic."""
    from formaltask.tasks.crud import get_tasks

    repo.create_epic("test-epic", "A test epic")

    task_id1 = repo.create_task(
        epic_name="test-epic",
        title="Task 1",
        description="First task",
        criteria=["Criterion 1"],
    )
    task_id2 = repo.create_task(
        epic_name="test-epic",
        title="Task 2",
        description="Second task",
        criteria=["Criterion 2"],
    )

    tasks = get_tasks(db_path, "test-epic")

    assert isinstance(tasks, list)
    assert len(tasks) == 2
    assert tasks[0]["id"] == task_id1
    assert tasks[1]["id"] == task_id2


def test_delete_task_verified_removes(db_path, repo):
    """P1: delete_task_verified removes task and criteria."""
    from formaltask.tasks.crud import delete_task_verified, get_task

    repo.create_epic("test-epic", "A test epic")

    task_id = repo.create_task(
        epic_name="test-epic",
        title="Task to Delete",
        description="Will be deleted",
        criteria=["Criterion 1", "Criterion 2"],
    )

    # Verify task exists
    assert get_task(db_path, task_id) is not None

    # Delete
    result = delete_task_verified(db_path, task_id)

    # Verify deleted
    assert result is True
    assert get_task(db_path, task_id) is None


def test_delete_task_verified_nonexistent_returns_false(db_path, repo):
    """P2: delete_task_verified returns False for nonexistent task."""
    from formaltask.tasks.crud import delete_task_verified

    result = delete_task_verified(db_path, 99999)

    assert result is False


# ============ Lifecycle Methods ============


def test_get_in_progress_tasks_returns_task_ids(db_path, repo):
    """P0 Regression: get_in_progress_tasks returns IDs of in_progress tasks.

    Regression test for SQL bug fix (Task #2414) - ensures correct join:
    - Uses epic_name = e.name (not epic_id = e.id)
    - Returns actual in-progress tasks (not empty list)
    """
    from formaltask.tasks.crud import get_in_progress_tasks
    from formaltask.tasks.lifecycle import transition_task_status

    repo.create_epic("test-epic", "A test epic")

    task_id1 = repo.create_task(
        epic_name="test-epic",
        title="Task 1",
        description="First task",
        criteria=["Criterion 1"],
    )
    _task_id2 = repo.create_task(  # Not started - should NOT appear in results
        epic_name="test-epic",
        title="Task 2",
        description="Second task",
        criteria=["Criterion 2"],
    )
    task_id3 = repo.create_task(
        epic_name="test-epic",
        title="Task 3",
        description="Third task",
        criteria=["Criterion 3"],
    )

    # Start task 1 and task 3 (making them in_progress)
    transition_task_status(db_path, task_id1, "in_progress")
    transition_task_status(db_path, task_id3, "in_progress")

    # Get in-progress tasks
    in_progress = get_in_progress_tasks(db_path, "test-epic")

    # Verify: should return both in_progress tasks, ordered by ID
    assert isinstance(in_progress, list)
    assert len(in_progress) == 2
    assert in_progress == [task_id1, task_id3]


def test_create_tasks_batch_unknown_epic_raises(db_path, repo):
    """P0: create_tasks_batch raises EpicNotFoundError for unknown epic."""
    from formaltask.exceptions import EpicNotFoundError
    from formaltask.tasks.crud import create_tasks_batch

    tasks = [
        {"title": "Task 1", "description": "Desc", "criteria": ["AC1"]},
    ]

    with pytest.raises(EpicNotFoundError) as exc_info:
        create_tasks_batch(db_path, "nonexistent-epic", tasks)

    assert exc_info.value.epic_name == "nonexistent-epic"


def test_create_tasks_batch_creates_multiple_tasks(db_path, repo):
    """P0: create_tasks_batch creates tasks and returns IDs in order."""
    from formaltask.tasks.crud import create_tasks_batch, get_task

    repo.create_epic("test-epic", "A test epic")

    tasks = [
        {"title": "Task 1", "description": "First", "criteria": ["AC1"]},
        {"title": "Task 2", "description": "Second", "criteria": ["AC2"]},
    ]

    task_ids = create_tasks_batch(db_path, "test-epic", tasks)

    assert isinstance(task_ids, list)
    assert len(task_ids) == 2
    # Verify tasks exist
    for task_id in task_ids:
        task = get_task(db_path, task_id)
        assert task is not None


# ============ Task #2833: create_tasks_batch dependency resolution ============


def test_create_tasks_batch_resolves_position_dependencies(db_path, repo):
    """P0: create_tasks_batch resolves 0-based position indices to task IDs.

    Task #2833: Dependency wiring moved from epic_decompose.py to crud.py.
    Position indices are 0-based (matching list index) in depends_on_positions.
    """

    from formaltask.tasks.crud import create_tasks_batch, get_task

    repo.create_epic("test-epic", "A test epic")

    # Create 3 tasks where Task 2 depends on Task 1 (position 0)
    # and Task 3 depends on both Task 1 and Task 2 (positions 0, 1)
    tasks = [
        {"title": "Task 1", "description": "First", "criteria": ["AC1"]},
        {
            "title": "Task 2",
            "description": "Second",
            "criteria": ["AC2"],
            "depends_on_positions": [0],  # depends on Task 1
        },
        {
            "title": "Task 3",
            "description": "Third",
            "criteria": ["AC3"],
            "depends_on_positions": [0, 1],  # depends on Task 1 and Task 2
        },
    ]

    task_ids = create_tasks_batch(db_path, "test-epic", tasks)

    assert len(task_ids) == 3

    # Verify Task 1 has no dependencies
    task1 = get_task(db_path, task_ids[0])
    assert task1["depends_on"] == [], "Task 1 should have no dependencies"

    # Verify Task 2 depends on Task 1
    task2 = get_task(db_path, task_ids[1])
    assert task_ids[0] in task2["depends_on"], "Task 2 should depend on Task 1"

    # Verify Task 3 depends on both Task 1 and Task 2
    task3 = get_task(db_path, task_ids[2])
    assert task_ids[0] in task3["depends_on"], "Task 3 should depend on Task 1"
    assert task_ids[1] in task3["depends_on"], "Task 3 should depend on Task 2"
    assert len(task3["depends_on"]) == 2


def test_create_tasks_batch_position_to_id_mapping(db_path, repo):
    """P1: create_tasks_batch correctly maps positions to IDs in insertion order.

    Ensures the position-to-ID mapping reflects the actual insert order.
    """
    from formaltask.tasks.crud import create_tasks_batch, get_task

    repo.create_epic("test-epic", "A test epic")

    tasks = [
        {"title": "Alpha", "description": "First", "criteria": ["AC1"]},
        {"title": "Beta", "description": "Second", "criteria": ["AC2"]},
        {
            "title": "Gamma",
            "description": "Third",
            "criteria": ["AC3"],
            "depends_on_positions": [1],  # depends on Beta (position 1)
        },
    ]

    task_ids = create_tasks_batch(db_path, "test-epic", tasks)

    # Verify Gamma depends on Beta (not Alpha)
    task_gamma = get_task(db_path, task_ids[2])
    assert task_ids[1] in task_gamma["depends_on"]
    assert task_ids[0] not in task_gamma["depends_on"]


def test_create_tasks_batch_invalid_position_raises(db_path, repo):
    """P0: create_tasks_batch raises ValueError for invalid position index.

    Invalid positions include negative indices and indices >= number of tasks.
    """
    from formaltask.tasks.crud import create_tasks_batch

    repo.create_epic("test-epic", "A test epic")

    # Position 5 is invalid (only 2 tasks being created)
    tasks = [
        {"title": "Task 1", "description": "First", "criteria": ["AC1"]},
        {
            "title": "Task 2",
            "description": "Second",
            "criteria": ["AC2"],
            "depends_on_positions": [5],  # Invalid: position 5 doesn't exist
        },
    ]

    with pytest.raises(ValueError, match="invalid dependency position"):
        create_tasks_batch(db_path, "test-epic", tasks)


def test_create_tasks_batch_forward_reference_raises(db_path, repo):
    """P0: create_tasks_batch rejects forward references.

    A task cannot depend on a task that comes after it in the list.
    """
    from formaltask.tasks.crud import create_tasks_batch

    repo.create_epic("test-epic", "A test epic")

    # Task 1 depends on Task 2 (forward reference, position 1 > position 0)
    tasks = [
        {
            "title": "Task 1",
            "description": "First",
            "criteria": ["AC1"],
            "depends_on_positions": [1],  # Forward reference to Task 2
        },
        {"title": "Task 2", "description": "Second", "criteria": ["AC2"]},
    ]

    with pytest.raises(ValueError, match="[Ff]orward reference"):
        create_tasks_batch(db_path, "test-epic", tasks)


# ============ Task #2859: Runnable acceptance criteria command storage ============


def test_create_tasks_batch_stores_command_from_dict_criteria(db_path, repo):
    """P0: create_tasks_batch stores command field when criteria is list[dict].

    Task #2859: Acceptance criteria can now have a command field for runnable AC.
    """
    from formaltask.db.connection import DatabaseConnection
    from formaltask.tasks.crud import create_tasks_batch

    repo.create_epic("test-epic", "A test epic")

    tasks = [
        {
            "title": "Task with runnable AC",
            "description": "Task desc",
            "criteria": [
                {"text": "Text criterion only", "command": None},
                {"text": "Runnable criterion", "command": "pytest tests/unit/"},
            ],
        },
    ]

    task_ids = create_tasks_batch(db_path, "test-epic", tasks)

    # Verify command was stored in database
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT text, command FROM acceptance_criteria WHERE task_id = ? ORDER BY id",
            (task_ids[0],),
        )
        rows = cursor.fetchall()

    assert len(rows) == 2
    assert rows[0]["text"] == "Text criterion only"
    assert rows[0]["command"] is None
    assert rows[1]["text"] == "Runnable criterion"
    assert rows[1]["command"] == "pytest tests/unit/"


def test_create_tasks_batch_handles_mixed_criteria_formats(db_path, repo):
    """P1: create_tasks_batch handles both string and dict criteria in same task.

    For backwards compatibility, criteria can be a mix of strings and dicts.
    """
    from formaltask.db.connection import DatabaseConnection
    from formaltask.tasks.crud import create_tasks_batch

    repo.create_epic("test-epic", "A test epic")

    tasks = [
        {
            "title": "Task with mixed criteria",
            "description": "Task desc",
            "criteria": [
                "Plain string criterion",  # string format (backwards compat)
                {"text": "Dict criterion with command", "command": "make test"},
            ],
        },
    ]

    task_ids = create_tasks_batch(db_path, "test-epic", tasks)

    # Verify both formats stored correctly
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT text, command FROM acceptance_criteria WHERE task_id = ? ORDER BY id",
            (task_ids[0],),
        )
        rows = cursor.fetchall()

    assert len(rows) == 2
    # String criterion: text extracted, command is NULL
    assert rows[0]["text"] == "Plain string criterion"
    assert rows[0]["command"] is None
    # Dict criterion: both text and command stored
    assert rows[1]["text"] == "Dict criterion with command"
    assert rows[1]["command"] == "make test"
