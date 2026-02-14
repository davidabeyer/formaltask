"""Resume workers from existing Claude sessions (e.g., after restart)."""

import argparse

from formaltask.cli.commands.spawn import send_enter_to_sessions
from formaltask.cli.context import CLIContext, with_repository
from formaltask.tasks import get_in_progress_tasks
from formaltask.workers.resume import (
    InvalidSessionIdError,
    SessionExpiredError,
    TmuxSpawnError,
    WorktreeNotFoundError,
    resume_worker_in_tmux,
)


def setup_parser(subparser):
    """Set up argument parser for resume command."""
    subparser.add_argument("task_ids", nargs="*", type=int)
    subparser.add_argument("--epic", dest="epic_name")
    subparser.add_argument("--db-path", default=None)
    subparser.add_argument("-m", "--message", default="Continue working on the task.")


@with_repository
def execute(ctx: CLIContext, args: argparse.Namespace) -> int:
    """Execute the resume command."""
    task_ids = args.task_ids or None
    epic_name = getattr(args, "epic_name", None)

    if task_ids and epic_name:
        print("Error: task_ids and --epic are mutually exclusive")
        return 1

    if epic_name:
        task_ids = get_in_progress_tasks(ctx.db_path, epic_name)
        if not task_ids:
            print(f"No in_progress tasks in epic '{epic_name}'")
            return 0

    if not task_ids:
        print("No task IDs. Use task IDs or --epic <name>")
        return 1

    resumed, failed = [], []
    for task_id in task_ids:
        try:
            session = resume_worker_in_tmux(task_id, args.message)
            resumed.append(task_id)
            print(f"Resumed #{task_id}: {session}")
        except (WorktreeNotFoundError, SessionExpiredError) as e:
            print(f"Skipped #{task_id}: {e}")
        except (InvalidSessionIdError, TmuxSpawnError) as e:
            failed.append(task_id)
            print(f"Failed #{task_id}: {e}")

    if resumed:
        send_enter_to_sessions(resumed, delay=10.0)
        print(f"\nResumed {len(resumed)} worker(s). Attach: tmux attach -t <session>")

    return 0 if resumed else (1 if failed else 0)
