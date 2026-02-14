"""pm task-defer command - Defer a task with a required reason."""

from formaltask.cli.base import CLIError
from formaltask.cli.context import with_db_path
from formaltask.cli.exit_codes import ExitCode
from formaltask.db.connection import DatabaseConnection
from formaltask.tasks.crud import defer_task


def setup_parser(subparser):
    """Set up argument parser for task-defer command."""
    subparser.add_argument("task_id", type=int, help="Task ID to defer")
    subparser.add_argument(
        "--reason",
        required=True,
        help="Reason for deferring (>= 20 characters required)",
    )
    subparser.add_argument(
        "--db-path",
        default=None,
        help="Database path (default: auto-detect)",
    )


@with_db_path
def execute(db_path: str, args) -> int:
    """Execute the task-defer command."""
    try:
        result = task_defer(args.task_id, reason=args.reason, db_path=db_path)
        print(f"✓ Deferred task #{result['task_id']}")
        return 0
    except CLIError as e:
        print(f"Error: {e.message}")
        return e.exit_code.value if hasattr(e.exit_code, "value") else int(e.exit_code)


def task_defer(task_id: int, reason: str, db_path: str) -> dict:
    """Defer a task with a required reason."""
    if len(reason) < 20:
        raise CLIError(
            "Defer reason must be at least 20 characters", exit_code=ExitCode.USAGE_ERROR
        )

    # Check if task exists and get status
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, status FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            raise CLIError(f"Task #{task_id} not found", exit_code=ExitCode.NOT_FOUND)
        status = row[1]
        if status == "completed":
            raise CLIError(
                f"Cannot defer completed task #{task_id}", exit_code=ExitCode.INVALID_STATE
            )
        if status == "deferred":
            raise CLIError(f"Task #{task_id} is already deferred", exit_code=ExitCode.INVALID_STATE)

    # Defer the task
    try:
        defer_task(db_path, task_id, reason)
    except ValueError as e:
        raise CLIError(str(e)) from e

    return {"task_id": task_id, "status": "deferred"}
