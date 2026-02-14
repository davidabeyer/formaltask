"""Task CRUD operations with db_path-first function signatures (Task #2724).

All functions follow the pattern:
    func(db_path: str, ...) -> ReturnType

These functions use DatabaseConnection directly, not the EpicRepository class.
"""

import json
from datetime import UTC, datetime

from formaltask.db.connection import DatabaseConnection
from formaltask.db.helpers import transaction
from formaltask.types import TaskData
from formaltask.utils.validation import validate_task_creation

__all__: list[str] = [
    "create_task",
    "create_tasks_batch",
    "defer_task",
    "delete_task_verified",
    "get_in_progress_tasks",
    "get_task",
    "get_tasks",
]


def create_task(
    db_path: str,
    epic_name: str,
    title: str,
    description: str,
    criteria: list[str] | list[dict],
    depends_on: list[int] | None = None,
    is_parallel: bool = False,
    metadata: dict | None = None,
    status: str | None = None,
) -> int:
    """Create a new task with acceptance criteria.

    Args:
        db_path: Path to SQLite database
        epic_name: Name of the epic this task belongs to
        title: Task title
        description: Task description
        criteria: List of acceptance criteria (strings or dicts with text+command)
        depends_on: List of task IDs this task depends on
        is_parallel: Whether task can run in parallel
        metadata: Additional metadata dict
        status: Initial status (defaults to "open")

    Returns:
        The ID of the created task.

    Raises:
        EpicNotFoundError: If the epic doesn't exist
        ValueError: If validation fails
    """
    from formaltask.exceptions import EpicNotFoundError

    validate_task_creation(title, description, criteria, metadata)

    # Validate spec metadata when artifact fields are present
    if metadata and ("artifact_type" in metadata or "artifact_content" in metadata):
        from formaltask.utils.schemas import SpecMetadata

        SpecMetadata.model_validate(metadata)

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        with transaction(conn):
            # Check epic exists
            cursor.execute("SELECT name FROM epics WHERE name = ?", (epic_name,))
            if cursor.fetchone() is None:
                raise EpicNotFoundError(epic_name)

            # Get next position for this epic
            cursor.execute(
                """SELECT COALESCE(MAX(position), 0) + 1
                   FROM tasks
                   WHERE epic_name = ?""",
                (epic_name,),
            )
            next_position = cursor.fetchone()[0]

            # Insert task
            created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            depends_on_json = json.dumps(depends_on if depends_on else [])
            metadata_json = json.dumps(metadata) if metadata else None
            task_status = status or "open"
            cursor.execute(
                """INSERT INTO tasks (epic_name, title, description, status, position, created_at, depends_on, is_parallel, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    epic_name,
                    title,
                    description,
                    task_status,
                    next_position,
                    created_at,
                    depends_on_json,
                    1 if is_parallel else 0,
                    metadata_json,
                ),
            )
            task_id = cursor.lastrowid

            # Insert acceptance criteria
            for criterion in criteria:
                # Handle both string and dict formats
                if isinstance(criterion, dict):
                    criterion_text = criterion.get("text", "")
                    criterion_command = criterion.get("command")
                else:
                    criterion_text = criterion
                    criterion_command = None
                cursor.execute(
                    """INSERT INTO acceptance_criteria (task_id, text, checked, command)
                       VALUES (?, ?, FALSE, ?)""",
                    (task_id, criterion_text, criterion_command),
                )

            return task_id  # type: ignore[return-value]


def get_task(db_path: str, task_id: int) -> TaskData | None:
    """Get task by ID.

    Args:
        db_path: Path to SQLite database
        task_id: ID of the task to retrieve

    Returns:
        TaskData dict or None if not found.
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, epic_name, title, description, status, position,
                      depends_on, created_at, started_at, completed_at,
                      is_parallel, metadata, artifacts_json,
                      defer_reason, cancel_reason, cancelled_at,
                      session_id, review_round, pr_url, artifact_type
               FROM tasks WHERE id = ?""",
            (task_id,),
        )
        row = cursor.fetchone()

        if row is None:
            return None

        # Parse metadata JSON if present
        metadata_raw = row[11]
        metadata = None
        if metadata_raw:
            try:
                metadata = json.loads(metadata_raw)
            except json.JSONDecodeError:
                metadata = None

        # Parse depends_on JSON
        depends_on_raw = row[6]
        depends_on = []
        if depends_on_raw:
            try:
                depends_on = json.loads(depends_on_raw)
            except json.JSONDecodeError:
                depends_on = []

        return {
            "id": row[0],
            "epic_name": row[1],
            "title": row[2],
            "description": row[3],
            "status": row[4],
            "position": row[5],
            "depends_on": depends_on,
            "created_at": row[7],
            "started_at": row[8],
            "completed_at": row[9],
            "is_parallel": bool(row[10]) if row[10] is not None else False,
            "metadata": metadata,
            "artifacts_json": row[12],
            "defer_reason": row[13],
            "cancel_reason": row[14],
            "cancelled_at": row[15],
            "session_id": row[16],
            "review_round": row[17],
            "pr_url": row[18],
            "artifact_type": row[19],
        }


def get_tasks(db_path: str, epic_name: str) -> list[dict]:
    """Get all tasks for an epic.

    Args:
        db_path: Path to SQLite database
        epic_name: Name of the epic

    Returns:
        List of TaskListItem dicts with id, title, status.
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, status FROM tasks WHERE epic_name = ? ORDER BY position",
            (epic_name,),
        )
        return [{"id": row[0], "title": row[1], "status": row[2]} for row in cursor.fetchall()]


def get_in_progress_tasks(db_path: str, epic_name: str) -> list[int]:
    """Get task IDs with status='in_progress' for an epic.

    Args:
        db_path: Path to SQLite database
        epic_name: Epic name to filter by

    Returns:
        List of task IDs currently in_progress.
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id FROM tasks
               WHERE epic_name = ? AND status = 'in_progress'
               ORDER BY id""",
            (epic_name,),
        )
        return [row[0] for row in cursor.fetchall()]


def create_tasks_batch(db_path: str, epic_name: str, tasks: list[dict]) -> list[int]:
    """Create multiple tasks in a batch operation.

    Args:
        db_path: Path to SQLite database
        epic_name: Name of epic to create tasks in
        tasks: List of task dicts with keys:
            - title: Task title (required)
            - description: Task description (required)
            - criteria: List of acceptance criteria strings (required)
            - depends_on_positions: List of 0-based position indices (optional)
            - depends_on: List of task IDs (optional, use depends_on_positions instead)
            - metadata: Dict of additional metadata (optional)
            - is_parallel: Whether task can run in parallel (optional)

    Returns:
        List of created task IDs in same order as input.

    Raises:
        EpicNotFoundError: If epic doesn't exist
        ValueError: If any task validation fails or invalid dependency positions
    """
    from formaltask.exceptions import EpicNotFoundError

    if not tasks:
        return []

    # Validate all tasks before database operations
    for idx, task in enumerate(tasks):
        validate_task_creation(
            task["title"],
            task["description"],
            task["criteria"],
            task.get("metadata"),
        )
        task_metadata = task.get("metadata")
        if task_metadata and (
            "artifact_type" in task_metadata or "artifact_content" in task_metadata
        ):
            from formaltask.utils.schemas import SpecMetadata

            SpecMetadata.model_validate(task_metadata)

        # Validate depends_on_positions (0-based indices)
        positions = task.get("depends_on_positions", [])
        for pos in positions:
            if pos < 0 or pos >= len(tasks):
                raise ValueError(
                    f"Task '{task['title']}' references invalid dependency position {pos}"
                )
            if pos >= idx:
                raise ValueError(
                    f"Task '{task['title']}': Forward reference not allowed "
                    f"(position {idx} cannot depend on position {pos})"
                )

    task_ids: list[int] = []
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        with transaction(conn):
            # Check epic exists
            cursor.execute("SELECT name FROM epics WHERE name = ?", (epic_name,))
            if cursor.fetchone() is None:
                raise EpicNotFoundError(epic_name)

            # Get starting position for this epic
            cursor.execute(
                """SELECT COALESCE(MAX(position), 0) + 1
                   FROM tasks WHERE epic_name = ?""",
                (epic_name,),
            )
            next_position = cursor.fetchone()[0]

            created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

            # Phase 1: Insert all tasks with empty depends_on
            for task in tasks:
                task_metadata = task.get("metadata")
                metadata_json = json.dumps(task_metadata) if task_metadata else None
                is_parallel = 1 if task.get("is_parallel", False) else 0

                cursor.execute(
                    """INSERT INTO tasks
                       (epic_name, title, description, status, position,
                        created_at, depends_on, is_parallel, metadata)
                       VALUES (?, ?, ?, 'open', ?, ?, '[]', ?, ?)""",
                    (
                        epic_name,
                        task["title"],
                        task["description"],
                        next_position,
                        created_at,
                        is_parallel,
                        metadata_json,
                    ),
                )
                task_id = cursor.lastrowid
                if task_id is None:
                    raise RuntimeError("lastrowid is None after INSERT")

                # Insert acceptance criteria
                for criterion in task["criteria"]:
                    # Handle both string and dict formats
                    if isinstance(criterion, dict):
                        criterion_text = criterion.get("text", "")
                        criterion_command = criterion.get("command")
                    else:
                        criterion_text = criterion
                        criterion_command = None
                    cursor.execute(
                        """INSERT INTO acceptance_criteria
                           (task_id, text, checked, command) VALUES (?, ?, FALSE, ?)""",
                        (task_id, criterion_text, criterion_command),
                    )

                task_ids.append(task_id)
                next_position += 1

            # Phase 2: Resolve position dependencies to task IDs and update
            for idx, task in enumerate(tasks):
                positions = task.get("depends_on_positions", [])

                if positions:
                    dep_ids = [task_ids[pos] for pos in positions]
                    depends_on_json = json.dumps(dep_ids)
                    cursor.execute(
                        "UPDATE tasks SET depends_on = ? WHERE id = ?",
                        (depends_on_json, task_ids[idx]),
                    )

    return task_ids


def defer_task(db_path: str, task_id: int, reason: str) -> None:
    """Defer task with reason.

    Args:
        db_path: Path to SQLite database
        task_id: ID of task to defer
        reason: Reason for deferral

    Raises:
        TaskNotFoundError: If task doesn't exist
        ValueError: If transition is invalid or validation fails
    """
    from pydantic import ValidationError

    from formaltask.db.helpers import ensure_task_exists
    from formaltask.utils.schemas import TaskMetadata
    from formaltask.utils.validation import validate_metadata_size

    # Validate metadata first (no DB changes yet)
    try:
        validated = TaskMetadata(defer_reason=reason)
        metadata_dict = validated.model_dump(exclude_none=True)
        validate_metadata_size(metadata_dict)
        metadata_json = validated.model_dump_json()
    except ValidationError as e:
        error_detail = e.errors()[0]
        field = error_detail["loc"][0] if error_detail["loc"] else "metadata"
        msg = error_detail["msg"]
        raise ValueError(f"Invalid {field}: {msg}") from e

    # Atomic transaction: update status and metadata together (fixes P0 race condition)
    with DatabaseConnection(db_path, exclusive=True) as conn:
        cursor = conn.cursor()

        # Verify task exists and can transition to deferred
        task = ensure_task_exists(cursor, task_id)
        current_status = task["status"]

        # Validate transition (deferred can come from open, in_progress, or blocked)
        valid_sources = ["open", "in_progress", "blocked"]
        if current_status not in valid_sources:
            raise ValueError(
                f"Cannot defer task from status '{current_status}'. "
                f"Valid source statuses: {', '.join(valid_sources)}"
            )

        # Update status and metadata atomically
        cursor.execute(
            "UPDATE tasks SET status = ?, metadata = ? WHERE id = ?",
            ("deferred", metadata_json, task_id),
        )


def delete_task_verified(db_path: str, task_id: int) -> bool:
    """Delete task and acceptance criteria with verification.

    Args:
        db_path: Path to SQLite database
        task_id: ID of task to delete

    Returns:
        True if task was deleted, False if task was not found.
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()

        # Check if task exists BEFORE transaction
        cursor.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
        if cursor.fetchone() is None:
            return False

        try:
            with transaction(conn):
                # Delete acceptance criteria first (foreign key order)
                cursor.execute(
                    "DELETE FROM acceptance_criteria WHERE task_id = ?",
                    (task_id,),
                )

                # Delete the task
                cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                task_deleted = cursor.rowcount

                # Verify deletion succeeded
                if task_deleted != 1:
                    raise RuntimeError("Deletion verification failed")

            return True

        except RuntimeError:
            return False
