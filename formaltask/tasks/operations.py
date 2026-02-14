"""Task metadata operations (Task #1658, #2711).

Task #2711: TaskOperations class has been inlined into EpicRepository.
This module now only contains:
- SCALAR_COLUMN_FIELDS: Set of metadata fields stored in columns
- update_task_metadata(): Standalone function for metadata updates
"""

import json

from formaltask.db.connection import DatabaseConnection
from formaltask.db.helpers import ensure_task_exists

# Task #2588: Scalar fields now stored in columns, not metadata JSON
SCALAR_COLUMN_FIELDS = {
    "defer_reason",
    "cancel_reason",
    "cancelled_at",
    "session_id",
    "review_round",
    "pr_url",
    "artifact_type",
}


def update_task_metadata(
    db_path: str,
    task_id: int,
    key: str,
    value,
    mode: str = "merge",
) -> None:
    """Single source of truth for task metadata modifications.

    Args:
        db_path: Path to database
        task_id: Task to update
        key: Metadata key to set (e.g., 'session_id', 'learnings')
        value: Value to set (will be JSON serialized for array/complex fields,
               stored directly for scalar column fields)
        mode: 'merge' (default) uses json_set, 'set' overwrites entire metadata

    Raises:
        TaskNotFoundError: If task doesn't exist
    """
    with DatabaseConnection(db_path, exclusive=True) as conn:
        cursor = conn.cursor()
        ensure_task_exists(cursor, task_id)

        # Task #2588: Route scalar fields to columns
        if key in SCALAR_COLUMN_FIELDS:
            # Safe: key validated against allowlist (SCALAR_COLUMN_FIELDS)
            # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
            cursor.execute(f"UPDATE tasks SET {key} = ? WHERE id = ?", (value, task_id))
        elif mode == "merge":
            # Use json() function to properly handle complex values (dicts, lists)
            # This ensures the value is stored as JSON, not as a string
            cursor.execute(
                """UPDATE tasks
                   SET metadata = json_set(COALESCE(metadata, '{}'), ?, json(?))
                   WHERE id = ?""",
                (f"$.{key}", json.dumps(value), task_id),
            )
        else:  # mode == 'set'
            cursor.execute(
                "UPDATE tasks SET metadata = ? WHERE id = ?",
                (json.dumps({key: value}), task_id),
            )
