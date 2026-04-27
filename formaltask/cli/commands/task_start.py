"""ft task start command."""

import argparse
import sys

from formaltask.cli.context import with_db_path
from formaltask.cli.exit_codes import ExitCode


def setup_parser(subparser):
    """Set up argument parser for task-start command."""
    subparser.add_argument(
        "task_id",
        type=int,
        help="Task ID to start (transition open → in_progress)",
    )
    subparser.add_argument(
        "--db-path",
        default=None,
        help="Database path (default: auto-detect)",
    )


@with_db_path
def execute(db_path: str, args: argparse.Namespace) -> int:
    """Execute the task-start command."""
    from formaltask.exceptions import TaskNotFoundError
    from formaltask.tasks.lifecycle import InvalidTransitionError, transition_task_status

    try:
        transition_task_status(db_path, args.task_id, "in_progress", idempotent=True)
        print(f"✓ Started task #{args.task_id}")
        return ExitCode.SUCCESS.value
    except TaskNotFoundError:
        print(f"Error: Task #{args.task_id} not found", file=sys.stderr)
        return ExitCode.NOT_FOUND.value
    except InvalidTransitionError as e:
        print(
            f"Error: Cannot start task #{args.task_id} from status '{e.current_status}'",
            file=sys.stderr,
        )
        return ExitCode.CONFLICT.value
