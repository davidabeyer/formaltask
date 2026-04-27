"""pm-epic-list command - List all epics with status."""

from __future__ import annotations

import json as json_module
import sqlite3
import sys

from formaltask.cli.context import with_db_path
from formaltask.cli.exit_codes import ExitCode
from formaltask.db.connection import DatabaseConnection

# Column names from epic_status VIEW (schema-v5.sql:202-222)
_EPIC_STATUS_COLUMNS = (
    "epic_name",
    "description",
    "skip_review",
    "created_at",
    "archived_at",
    "total_tasks",
    "completed_tasks",
    "in_progress_tasks",
    "status",
    "reviewed_at",
)


def _get_extra_epic_data(db_path: str, epic_names: list[str]) -> dict[str, dict]:
    """Get cancelled counts, last activity, and spawnable count for epics.

    Returns dict keyed by epic_name with 'cancelled', 'last_activity', and 'spawnable'.
    """
    if not epic_names:
        return {}

    placeholders = ",".join("?" * len(epic_names))

    # Main query for cancelled and last_activity
    query = f"""
        SELECT
            epic_name,
            SUM(CASE WHEN status IN ('cancelled', 'blocked', 'deferred', 'blocked_user') THEN 1 ELSE 0 END) as cancelled,
            date(MAX(COALESCE(completed_at, started_at, spawned_at, created_at))) as last_activity
        FROM tasks
        WHERE epic_name IN ({placeholders})
        GROUP BY epic_name
    """  # noqa: S608 - placeholders are parameterized

    # Spawnable query using existing view
    spawnable_query = f"""
        SELECT epic_name, COUNT(*) as spawnable
        FROM task_ready_status
        WHERE epic_name IN ({placeholders})
        GROUP BY epic_name
    """  # noqa: S608 - placeholders are parameterized

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
        cursor.execute(query, epic_names)
        result = {
            row[0]: {"cancelled": row[1], "last_activity": row[2], "spawnable": 0}
            for row in cursor.fetchall()
        }
        # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
        cursor.execute(spawnable_query, epic_names)
        for row in cursor.fetchall():
            if row[0] in result:
                result[row[0]]["spawnable"] = row[1]

        return result


def epic_list(
    db_path: str,
    *,
    show_archived: bool = False,
    json_mode: bool = False,
    search: str | None = None,
) -> dict | None:
    """List all epics with status information.

    Args:
        db_path: Path to the database
        show_archived: Include archived epics (default: False)
        json_mode: Return structured data for JSON output (default: False)
        search: Filter by epic_name or description (case-insensitive, LIKE-escaped)

    Returns:
        dict: {"epics": [...]} when json_mode=True
        None: When json_mode=False (prints to stdout)

    Raises:
        sqlite3.OperationalError: If epic_status VIEW doesn't exist
    """
    columns = ", ".join(_EPIC_STATUS_COLUMNS)
    query = f"SELECT {columns} FROM epic_status"  # noqa: S608 - columns are hardcoded
    conditions = []
    params: list[str] = []
    if not show_archived:
        conditions.append("archived_at IS NULL")
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        conditions.append("(epic_name LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')")
        params.extend([pattern, pattern])
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC"

    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            # Safe: query built from hardcoded column names and table, params are bound
            # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
            cursor.execute(  # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query
                query, params
            )
            rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        if "no such table: epic_status" in str(e):
            raise sqlite3.OperationalError(
                "epic_status VIEW not found. Database may need migration."
            ) from e
        raise

    # Get extra data (cancelled counts, last activity)
    epic_names = [row[0] for row in rows]
    extra_data = _get_extra_epic_data(db_path, epic_names)

    # Build structured data using helper
    epic_list_data = []
    for row in rows:
        epic = dict(zip(_EPIC_STATUS_COLUMNS, row, strict=True))
        extra = extra_data.get(
            epic["epic_name"], {"cancelled": 0, "last_activity": None, "spawnable": 0}
        )
        epic_list_data.append(
            {
                "name": epic["epic_name"],
                "description": epic["description"],
                "status": epic["status"],
                "created": epic["created_at"][:10] if epic["created_at"] else None,
                "last_activity": extra["last_activity"],
                "total_tasks": epic["total_tasks"],
                "completed_tasks": epic["completed_tasks"],
                "in_progress_tasks": epic["in_progress_tasks"],
                "cancelled_tasks": extra["cancelled"],
                "spawnable_tasks": extra["spawnable"],
            }
        )

    if json_mode:
        return {"epics": epic_list_data}

    # Print behavior
    if not rows:
        print("No epics found.")
        return None

    print(
        f"{'EPIC':<30} {'STATUS':<12} {'CREATED':<10} {'LAST':<10} {'TASKS':<6} {'DONE':<5} {'ACTIVE':<6} {'CANCEL':<6} {'SPAWN':<5}"
    )
    print("-" * 100)

    for data in epic_list_data:
        created = data["created"] or "-"
        last = data["last_activity"] or "-"
        print(
            f"{data['name']:<30} {data['status']:<12} {created:<10} {last:<10} "
            f"{data['total_tasks']:<6} {data['completed_tasks']:<5} {data['in_progress_tasks']:<6} {data['cancelled_tasks']:<6} {data['spawnable_tasks']:<5}"
        )

    print(f"\nTotal: {len(rows)} epics")
    return None


def setup_parser(subparser):
    """Set up argument parser for epic-list command."""
    subparser.add_argument(
        "--archived",
        action="store_true",
        help="Include archived epics",
    )
    subparser.add_argument(
        "--names",
        action="store_true",
        help="Output only epic names, one per line (for scripting)",
    )
    subparser.add_argument(
        "--search",
        "-s",
        help="Filter epics by name or description (case-insensitive)",
    )
    subparser.add_argument(
        "--db-path",
        default=None,
        help="Path to database (default: auto-detect)",
    )


@with_db_path
def execute(db_path: str, args) -> int:
    """Execute the epic-list command."""
    json_output = getattr(args, "json", False)
    names_only = getattr(args, "names", False)

    try:
        result = epic_list(
            db_path=db_path,
            show_archived=getattr(args, "archived", False),
            json_mode=json_output or names_only,  # Need structured data for --names
            search=getattr(args, "search", None),
        )

        if names_only and result is not None:
            for epic in result["epics"]:
                print(epic["name"])
            return 0

        if json_output and result is not None:
            print(json_module.dumps({"success": True, "data": result}))

        return 0

    except sqlite3.Error as e:
        if json_output:
            print(json_module.dumps({"success": False, "error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return ExitCode.GENERAL_ERROR.value
