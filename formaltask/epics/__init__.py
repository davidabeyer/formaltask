"""Epic standalone functions (Task #2723).

Functions extracted from EpicRepository, taking db_path as first parameter.
"""

from datetime import UTC, datetime

from formaltask.db.connection import DatabaseConnection
from formaltask.types import EpicData

__all__ = [
    "archive_epic",
    "create_epic",
    "get_epic",
    "get_epic_status",
    "list_epics",
    "mark_reviewed",
    "unarchive_epic",
    "update_epic",
]


def create_epic(db_path: str, name: str, description: str, skip_review: bool = False) -> None:
    """Create a new epic.

    Args:
        db_path: Path to SQLite database
        name: Unique epic name
        description: Epic description
        skip_review: Whether to skip review phase (default: False)

    Raises:
        sqlite3.IntegrityError: If epic with same name already exists
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO epics (name, description, skip_review, created_at) VALUES (?, ?, ?, ?)",
            (
                name,
                description,
                skip_review,
                datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )


def get_epic(db_path: str, name: str) -> EpicData | None:
    """Get epic by name.

    Args:
        db_path: Path to SQLite database
        name: Epic name to look up

    Returns:
        EpicData dict if found, None otherwise
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, description, skip_review, created_at, archived_at FROM epics WHERE name = ?",
            (name,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "name": row[0],
                "description": row[1],
                "skip_review": row[2],
                "created_at": row[3],
                "archived_at": row[4],
            }
        return None


def update_epic(
    db_path: str,
    name: str,
    description: str | None = None,
    feature_branch: str | None = None,
    reviewed_at: str | None = None,
) -> None:
    """Update an existing epic's attributes.

    Args:
        db_path: Path to SQLite database
        name: Epic name to update
        description: New description (optional)
        feature_branch: New feature branch (optional)
        reviewed_at: New reviewed timestamp (optional)

    Raises:
        ValueError: If epic not found or no updates provided
    """
    updates = []
    params: list[str] = []
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if feature_branch is not None:
        updates.append("feature_branch = ?")
        params.append(feature_branch)
    if reviewed_at is not None:
        updates.append("reviewed_at = ?")
        params.append(reviewed_at)

    if not updates:
        raise ValueError("No updates provided")

    params.append(name)

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
        cursor.execute(f"UPDATE epics SET {', '.join(updates)} WHERE name = ?", params)
        if cursor.rowcount == 0:
            raise ValueError(f"Epic '{name}' not found")


def archive_epic(db_path: str, name: str, force: bool = False) -> None:
    """Archive an epic.

    Args:
        db_path: Path to SQLite database
        name: Name of epic to archive
        force: If False, raise ValueError if epic has incomplete tasks

    Raises:
        ValueError: If epic doesn't exist
        ValueError: If force=False and epic has incomplete tasks
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()

        # Check if epic exists and get archived_at status
        cursor.execute("SELECT archived_at FROM epics WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Epic '{name}' not found")

        # If already archived, operation is idempotent
        if row[0] is not None:
            return

        # Check for incomplete tasks when force=False
        if not force:
            cursor.execute(
                "SELECT COUNT(*) FROM tasks WHERE epic_name = ? AND status NOT IN ('completed', 'cancelled')",
                (name,),
            )
            incomplete_count = cursor.fetchone()[0]
            if incomplete_count > 0:
                raise ValueError(
                    f"Cannot archive epic with {incomplete_count} incomplete tasks. "
                    "Use force=True to archive anyway."
                )

        cursor.execute(
            "UPDATE epics SET archived_at = ? WHERE name = ?",
            (datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), name),
        )


def unarchive_epic(db_path: str, name: str) -> None:
    """Unarchive an epic by clearing archived_at timestamp.

    Args:
        db_path: Path to SQLite database
        name: Name of epic to unarchive

    Raises:
        ValueError: If epic doesn't exist
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()

        # Check if epic exists
        cursor.execute("SELECT archived_at FROM epics WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Epic '{name}' not found")

        # If not archived, operation is idempotent
        if row[0] is None:
            return

        cursor.execute("UPDATE epics SET archived_at = NULL WHERE name = ?", (name,))


def get_epic_status(db_path: str, name: str) -> dict | None:
    """Get computed epic status from VIEW.

    Args:
        db_path: Path to SQLite database
        name: Epic name to get status for

    Returns:
        Dict with name, total_tasks, completed, in_progress, status
        or None if epic not found
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT epic_name, total_tasks, completed_tasks, in_progress_tasks, status
               FROM epic_status WHERE epic_name = ?""",
            (name,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "name": row[0],
            "total_tasks": row[1],
            "completed": row[2],
            "in_progress": row[3],
            "status": row[4],
        }


def mark_reviewed(db_path: str, name: str) -> None:
    """Mark epic as reviewed with current timestamp.

    Args:
        db_path: Path to SQLite database
        name: Name of epic to mark as reviewed

    Raises:
        ValueError: If epic not found or already archived
    """
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with DatabaseConnection(db_path, exclusive=True) as conn:
        cursor = conn.cursor()
        # Check epic exists and not archived
        cursor.execute(
            "SELECT name, archived_at FROM epics WHERE name = ?",
            (name,),
        )
        result = cursor.fetchone()
        if result is None:
            raise ValueError(f"Epic '{name}' not found")
        if result[1] is not None:
            raise ValueError(f"Epic '{name}' is archived")

        cursor.execute(
            "UPDATE epics SET reviewed_at = ? WHERE name = ?",
            (now, name),
        )


def list_epics(db_path: str) -> list[EpicData]:
    """List all epics.

    Args:
        db_path: Path to SQLite database

    Returns:
        List of EpicData dicts
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, description, skip_review, created_at, archived_at FROM epics ORDER BY created_at"
        )
        return [
            {
                "name": row[0],
                "description": row[1],
                "skip_review": row[2],
                "created_at": row[3],
                "archived_at": row[4],
            }
            for row in cursor.fetchall()
        ]
