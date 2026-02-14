"""pm learning command - Capture worker learnings to task metadata."""

import json
import sys

from formaltask.cli.exit_codes import ExitCode
from formaltask.db.path import get_db_path
from formaltask.utils.constants import TaskStatus
from formaltask.workers.context import get_task_id_from_session

# Plugin interface exports
COMMAND_NAME = "learning"
COMMAND_HELP = "Capture a learning (optionally target siblings with --for)"


def setup_parser(subparser):
    """Set up argument parser for learning command."""
    subparser.add_argument(
        "learning",
        help="Learning to capture (max 200 chars)",
    )
    subparser.add_argument(
        "--for",
        dest="targets",
        metavar="TASK_IDS",
        help="Target sibling task IDs (comma-separated). Omit to capture for self.",
    )
    subparser.add_argument(
        "--db-path",
        help="Database path (default: auto-detect)",
    )


def _parse_target_ids(targets_str: str) -> list[int] | str:
    """Parse comma-separated task IDs into list of integers.

    Returns list of integers on success, or error message string on failure.
    """
    try:
        ids = [int(tid.strip()) for tid in targets_str.split(",") if tid.strip()]
        if not ids:
            return "No valid target IDs provided"
        return ids
    except ValueError:
        return "Invalid target ID (must be integers)"


def _validate_targets(conn, source_task_id: int, target_ids: list[int]) -> str | None:
    """Validate target tasks. Returns error message or None if valid."""
    # Check for self-reference
    if source_task_id in target_ids:
        return "Cannot target self"

    # Get source task's epic
    source_row = conn.execute(
        "SELECT epic_name FROM tasks WHERE id = ?", (source_task_id,)
    ).fetchone()
    if not source_row:
        return f"Source task {source_task_id} not found"
    source_epic_name = source_row[0]

    # Validate each target
    for target_id in target_ids:
        row = conn.execute(
            "SELECT epic_name, status FROM tasks WHERE id = ?", (target_id,)
        ).fetchone()
        if not row:
            return f"Target task {target_id} not found"

        target_epic_name, target_status = row

        if target_epic_name != source_epic_name:
            return f"Target task {target_id} is in a different epic"

        if target_status == TaskStatus.COMPLETED.value:
            return f"Target task {target_id} is already completed"

    return None


def execute(args) -> int:
    """Execute the learning command."""
    from formaltask.db.connection import DatabaseConnection

    db_path = getattr(args, "db_path", None) or get_db_path()
    learning = args.learning.strip()

    # Validate empty
    if not learning:
        print("Learning cannot be empty", file=sys.stderr)
        return ExitCode.VALIDATION_ERROR.value

    # Validate length
    if len(learning) > 200:
        print(f"Learning too long ({len(learning)} chars). Max 200.", file=sys.stderr)
        return ExitCode.VALIDATION_ERROR.value

    # Get task ID from environment
    task_id = get_task_id_from_session()
    if task_id is None:
        print("No task context. Run from worker session.", file=sys.stderr)
        return ExitCode.NOT_FOUND.value

    # Parse and validate target IDs (if provided)
    target_ids = []
    if args.targets:
        target_ids = _parse_target_ids(args.targets)
        if isinstance(target_ids, str):
            print(target_ids, file=sys.stderr)
            return ExitCode.VALIDATION_ERROR.value

    with DatabaseConnection(db_path) as conn:
        # Validate targets (only if targeting siblings)
        if target_ids:
            error = _validate_targets(conn, task_id, target_ids)
            if error:
                print(error, file=sys.stderr)
                if "not found" in error.lower():
                    return ExitCode.NOT_FOUND.value
                return ExitCode.VALIDATION_ERROR.value

        # Store learning as object with text and targets (empty list = self-capture)
        learning_obj = json.dumps({"text": learning, "targets": target_ids})

        # Atomic update using SQLite JSON functions (prevents lost updates)
        # json_set: updates the learnings key in metadata
        # json_insert with $[#]: appends to array (# = array length = next index)
        # COALESCE: handles NULL metadata and missing learnings key
        result = conn.execute(
            """UPDATE tasks SET metadata = json_set(
                COALESCE(metadata, '{}'),
                '$.learnings',
                json_insert(
                    COALESCE(json_extract(metadata, '$.learnings'), json('[]')),
                    '$[#]',
                    json(?)
                )
            ) WHERE id = ?""",
            (learning_obj, task_id),
        )
        if result.rowcount == 0:
            print(f"Task {task_id} not found", file=sys.stderr)
            return ExitCode.NOT_FOUND.value

    print(f"Learning captured: {learning}")
    return ExitCode.SUCCESS.value
