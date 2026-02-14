"""ft task cancel command."""

import argparse

from formaltask.cli.context import with_db_path
from formaltask.cli.exit_codes import ExitCode


def setup_parser(subparser):
    """Set up argument parser for task-cancel command."""
    subparser.add_argument(
        "task_id",
        type=str,
        help="Task ID(s) to cancel (comma-separated for bulk cancel)",
    )
    subparser.add_argument(
        "--reason",
        required=True,
        help="Cancellation reason (min 20 characters)",
    )
    subparser.add_argument(
        "--force-terminal",
        action="store_true",
        dest="force_terminal",
        help="Allow cancelling tasks in terminal states (completed/cancelled) for data repair",
    )
    subparser.add_argument(
        "--db-path",
        default=None,
        help="Database path (default: auto-detect)",
    )


@with_db_path
def execute(db_path: str, args: argparse.Namespace) -> int:
    """Execute the task-cancel command.

    Simplified behavior: Cancel always succeeds. If dependents exist,
    print them as an informational note (not an error).
    """
    from formaltask.exceptions import TaskNotFoundError
    from formaltask.tasks.dependencies import get_dependent_tasks
    from formaltask.tasks.lifecycle import InvalidTransitionError, transition_task_status
    from formaltask.tasks.operations import update_task_metadata

    force_terminal = getattr(args, "force_terminal", False)

    # Parse comma-separated task IDs with validation
    try:
        task_ids = [int(x.strip()) for x in args.task_id.split(",") if x.strip()]
    except ValueError:
        print(f"Error: Invalid task ID(s): {args.task_id}")
        return ExitCode.USAGE_ERROR.value

    if not task_ids:
        print("Error: No valid task IDs provided")
        return ExitCode.USAGE_ERROR.value

    if len(args.reason) < 20:
        print(f"Error: Reason must be at least 20 characters (got {len(args.reason)})")
        return ExitCode.USAGE_ERROR.value

    try:
        # Process each task
        for task_id in task_ids:
            # Get dependents for informational message
            dependents = get_dependent_tasks(db_path, task_id)

            # Cancel the task (no blocking)
            transition_task_status(
                db_path, task_id, "cancelled", force=force_terminal, idempotent=force_terminal
            )

            # Store cancel reason using centralized function (routes to column per Task #2588)
            update_task_metadata(db_path, task_id, "cancel_reason", args.reason)

            # Print success message
            print(f"✓ Task #{task_id} cancelled")
            if dependents:
                ids = [d["id"] for d in dependents]
                print(f"  Note: Tasks {ids} depend on this and are now blocked")

        return ExitCode.SUCCESS.value

    except TaskNotFoundError as e:
        print(f"Error: Task #{e.task_id} not found")
        return ExitCode.NOT_FOUND.value
    except InvalidTransitionError as e:
        # Handle terminal state errors with helpful guidance
        if e.current_status in ("completed", "cancelled"):
            print(f"Error: Cannot cancel task - already in terminal state '{e.current_status}'")
            print()
            print("Use --force-terminal for data repair:")
            print(f'  ft task cancel {args.task_id} --reason "{args.reason}" --force-terminal')
            return ExitCode.CONFLICT.value
        print(f"Error: {e}")
        return ExitCode.CONFLICT.value
