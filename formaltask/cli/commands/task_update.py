"""Task update command for in-situ task editing (Task #1320)."""

import argparse
import json
import sys

from formaltask.cli.base import CLIError
from formaltask.cli.context import with_db_path
from formaltask.cli.exit_codes import ExitCode
from formaltask.db.connection import DatabaseConnection
from formaltask.tasks.dependencies import update_task_dependencies


def setup_parser(subparser):
    """Set up argument parser for task-update command."""
    subparser.add_argument("task_id", type=int, help="Task ID to update")
    subparser.add_argument("--title", type=str, help="New title for the task")
    subparser.add_argument("--description", type=str, help="New description for the task")
    subparser.add_argument(
        "--add-criteria", type=str, dest="add_criteria", help="Add acceptance criterion text"
    )
    subparser.add_argument(
        "--remove-criteria",
        type=int,
        dest="remove_criteria",
        help="Remove acceptance criterion by index (0-based)",
    )
    subparser.add_argument(
        "--reset-status",
        action="store_true",
        dest="reset_status",
        help="Reset status from in_progress to open (orphan recovery)",
    )
    subparser.add_argument(
        "--metadata",
        type=str,
        dest="metadata_json",
        help="JSON to merge into task metadata (e.g., '{\"critique_count\": 1}')",
    )
    subparser.add_argument(
        "--depends-on",
        type=int,
        action="append",
        dest="depends_on",
        help="Task ID this task depends on (can be used multiple times)",
    )
    subparser.add_argument(
        "--clear-deps",
        action="store_true",
        dest="clear_deps",
        help="Remove all dependencies (sets depends_on to [])",
    )
    subparser.add_argument(
        "--due-date",
        type=str,
        dest="due_date",
        help="Set due date (YYYY-MM-DD format)",
    )
    subparser.add_argument(
        "--priority",
        type=int,
        dest="priority",
        help="Set priority level (1=highest)",
    )
    subparser.add_argument(
        "--db-path",
        default=None,
        help="Database path (default: auto-detect)",
    )
    # Hidden trap: callers historically passed `--status X` here even though
    # state transitions belong to dedicated verbs. Accept silently (SUPPRESS
    # hides from --help) and emit a verb-mapping hint in execute().
    subparser.add_argument("--status", type=str, help=argparse.SUPPRESS)


@with_db_path
def execute(db_path: str, args) -> int:
    """Execute the task-update command."""
    try:
        if getattr(args, "status", None):
            print(
                "Error: `ft task update` does not change state. Use a dedicated verb:\n"
                "  --status active         →  ft task start <id>\n"
                "  --status completed      →  ft task complete <id>\n"
                '  --status cancelled      →  ft task cancel <id> --reason "<20+ chars>"\n'
                '  --status deferred       →  ft task defer <id> --reason "<reason>"\n'
                "  --status review         →  ft task complete <id>  (review folded into complete)\n"
                '  --status blocked        →  ft work blocked "<question>"  (positional; FT_TASK_ID from env)\n'
                "  (reset in_progress→open) →  ft task update <id> --reset-status",
                file=sys.stderr,
            )
            return 1
        # Check for mutually exclusive flags
        if getattr(args, "depends_on", None) and getattr(args, "clear_deps", False):
            print("Error: --depends-on and --clear-deps are mutually exclusive", file=sys.stderr)
            return 1
        if getattr(args, "title", None):
            task_update_title(args.task_id, args.title, db_path)
            print(f"✓ Updated task #{args.task_id} title")
        elif getattr(args, "description", None):
            task_update_description(args.task_id, args.description, db_path)
            print(f"✓ Updated task #{args.task_id} description")
        elif getattr(args, "add_criteria", None):
            task_update_add_criteria(args.task_id, args.add_criteria, db_path)
            print(f"✓ Added criterion to task #{args.task_id}")
        elif getattr(args, "remove_criteria", None) is not None:
            task_update_remove_criteria(args.task_id, args.remove_criteria, db_path)
            print(f"✓ Removed criterion from task #{args.task_id}")
        elif getattr(args, "reset_status", False):
            task_update_reset_status(args.task_id, db_path)
            print(f"✓ Reset task #{args.task_id} status to open")
        elif getattr(args, "metadata_json", None):
            task_update_metadata(args.task_id, args.metadata_json, db_path)
            print(f"✓ Updated task #{args.task_id} metadata")
        elif getattr(args, "depends_on", None):
            task_update_dependencies(args.task_id, args.depends_on, db_path)
            print(f"✓ Updated task #{args.task_id} dependencies")
        elif getattr(args, "clear_deps", False):
            task_update_dependencies(args.task_id, [], db_path)
            print(f"✓ Cleared task #{args.task_id} dependencies")
        elif getattr(args, "due_date", None):
            _update_field(args.task_id, "due_date", args.due_date, db_path)
            print(f"✓ Updated task #{args.task_id} due date to {args.due_date}")
        elif getattr(args, "priority", None) is not None:
            _update_field(args.task_id, "priority", str(args.priority), db_path)
            print(f"✓ Updated task #{args.task_id} priority to {args.priority}")
        else:
            print(
                "Error: Specify an update flag (--title, --description, --add-criteria, --remove-criteria, --reset-status, --metadata, --depends-on, --clear-deps, --due-date, --priority)",
                file=sys.stderr,
            )
            return 1
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def _validate_task_editable(cursor, task_id: int) -> None:
    """Check task exists and is editable (not completed/cancelled)."""
    cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if row is None:
        raise CLIError(f"Task #{task_id} not found", exit_code=ExitCode.NOT_FOUND)
    status = row[0]
    if status == "completed":
        raise ValueError(f"Cannot edit completed task #{task_id}")
    if status == "cancelled":
        raise ValueError(f"Cannot edit cancelled task #{task_id}")


# Defense-in-depth: callers in this module pass only literals, but _update_field
# accepts an arbitrary `field` string and interpolates it into raw SQL. Any future
# call site with user input could inject. Limit to the columns the wrappers below
# actually handle.
UPDATABLE_FIELDS = frozenset({"title", "description", "due_date", "priority"})


def _update_field(task_id: int, field: str, new_value: str, db_path: str) -> dict:
    """Update a single task field."""
    if field not in UPDATABLE_FIELDS:
        raise ValueError(
            f"Field '{field}' is not in UPDATABLE_FIELDS allowlist {sorted(UPDATABLE_FIELDS)}"
        )
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        _validate_task_editable(cursor, task_id)
        # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
        cursor.execute(f"SELECT {field} FROM tasks WHERE id = ?", (task_id,))
        old_value = cursor.fetchone()[0]
        # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
        cursor.execute(f"UPDATE tasks SET {field} = ? WHERE id = ?", (new_value, task_id))
        conn.commit()
        return {"task_id": task_id, "field": field, "old_value": old_value, "new_value": new_value}


def task_update_title(task_id: int, new_title: str, db_path: str) -> dict:
    return _update_field(task_id, "title", new_title, db_path)


def task_update_description(task_id: int, new_description: str, db_path: str) -> dict:
    return _update_field(task_id, "description", new_description, db_path)


def task_update_add_criteria(task_id: int, criterion_text: str, db_path: str) -> dict:
    """Add acceptance criterion to task.

    Uses the acceptance_criteria table (same as task creation) for consistency.
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        _validate_task_editable(cursor, task_id)
        cursor.execute(
            "INSERT INTO acceptance_criteria (task_id, text, checked) VALUES (?, ?, FALSE)",
            (task_id, criterion_text),
        )
        conn.commit()
        return {
            "task_id": task_id,
            "action": "add_criteria",
            "criterion": criterion_text,
        }


def task_update_remove_criteria(task_id: int, index: int, db_path: str) -> dict:
    """Remove acceptance criterion from task by index.

    Uses the acceptance_criteria table (same as task creation) for consistency.
    Index is 0-based, ordered by criterion ID (insertion order).
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        _validate_task_editable(cursor, task_id)
        # Get all criteria for this task ordered by ID (insertion order)
        cursor.execute(
            "SELECT id, text FROM acceptance_criteria WHERE task_id = ? ORDER BY id",
            (task_id,),
        )
        criteria = cursor.fetchall()
        if index < 0 or index >= len(criteria):
            raise ValueError(f"Invalid criteria index {index} for task #{task_id}")
        criterion_id = criteria[index][0]
        removed_text = criteria[index][1]
        cursor.execute("DELETE FROM acceptance_criteria WHERE id = ?", (criterion_id,))
        conn.commit()
        return {
            "task_id": task_id,
            "action": "remove_criteria",
            "removed": removed_text,
        }


def task_update_reset_status(task_id: int, db_path: str) -> dict:
    """Reset task from in_progress to open (orphan recovery)."""
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Task #{task_id} not found")
        old_status = row[0]
        if old_status != "in_progress":
            raise ValueError(f"Can only reset in_progress tasks, task #{task_id} is {old_status}")
        cursor.execute(
            "UPDATE tasks SET status = 'open', started_at = NULL WHERE id = ?",
            (task_id,),
        )
        conn.commit()
    return {"task_id": task_id, "old_status": old_status, "new_status": "open"}


def task_update_metadata(task_id: int, metadata_json: str, db_path: str) -> dict:
    """Merge JSON into task metadata."""
    try:
        new_metadata = json.loads(metadata_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        _validate_task_editable(cursor, task_id)
        cursor.execute("SELECT metadata FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        existing = json.loads(row[0]) if row[0] else {}
        merged = {**existing, **new_metadata}
        cursor.execute("UPDATE tasks SET metadata = ? WHERE id = ?", (json.dumps(merged), task_id))
        conn.commit()
        return {
            "task_id": task_id,
            "field": "metadata",
            "merged_keys": list(new_metadata.keys()),
        }


def task_update_dependencies(task_id: int, depends_on_ids: list[int], db_path: str) -> dict:
    """Update task dependencies."""
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        _validate_task_editable(cursor, task_id)
    update_task_dependencies(db_path, task_id, depends_on_ids)
    return {"task_id": task_id, "depends_on": depends_on_ids}
