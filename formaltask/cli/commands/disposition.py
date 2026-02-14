"""CLI disposition command - mark review findings with dispositions."""

import os
import sys

from formaltask.cli.context import with_db_path
from formaltask.cli.exit_codes import ExitCode
from formaltask.db.connection import DatabaseConnection
from formaltask.state.session import get_current_task
from formaltask.tasks.lifecycle import InvalidTransitionError, transition_task_status
from formaltask.utils.constants import DispositionType
from formaltask.workers.disposition import add_wontfix_entry, delete_wontfix_entry


def setup_parser(subparser):
    subparser.add_argument("file", nargs="?", help="File path")
    subparser.add_argument("line", type=int, nargs="?", help="Line number")
    subparser.add_argument("--reason", help="Reason for marking disposition")
    subparser.add_argument("--task", type=int, help="Task ID")
    subparser.add_argument("--list", action="store_true", help="List dispositions")
    subparser.add_argument("--clear", action="store_true", help="Clear entry")
    subparser.add_argument("--db-path", help="Database path")
    group = subparser.add_mutually_exclusive_group()
    group.add_argument("--needshuman", action="store_true", help="Needs human review (blocks task)")
    group.add_argument("--fixed", action="store_true", help="Fixed in this PR")


def _list_dispositions(task_id: int, db_path: str) -> None:
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT file, line, disposition, reason FROM finding_dispositions WHERE task_id = ?",
            (task_id,),
        )
        rows = cursor.fetchall()

    if not rows:
        print("No dispositions recorded.")
        return

    print(f"\nDispositions for Task #{task_id}")
    print(f"{'File:Line':<30} {'Status':<12} {'Reason'}")
    print("-" * 70)
    for file, line, disposition, reason in rows:
        loc = f"{file}:{line}" if line else file
        reason_short = reason[:40] + "..." if len(reason) > 43 else reason
        print(f"{loc:<30} {disposition:<12} {reason_short}")


def _block_task(db_path: str, task_id: int, file: str, line: int, reason: str) -> int:
    try:
        transition_task_status(db_path, task_id, "blocked_user")
    except InvalidTransitionError as e:
        print(f"Cannot block task: {e}", file=sys.stderr)
        return ExitCode.INVALID_STATE.value
    with DatabaseConnection(db_path, exclusive=True) as conn:
        conn.cursor().execute(
            "UPDATE tasks SET blocked_question = ? WHERE id = ?",
            (f"{file}:{line} {reason}", task_id),
        )
        conn.commit()
    print("Human can resolve via: /inbox")
    return 0


@with_db_path
def execute(db_path: str, args):
    task_id = args.task
    if task_id is None:
        task_id = get_current_task(db_path, os.getcwd())
    if task_id is None:
        print("No task specified. Use --task or start a session.", file=sys.stderr)
        return ExitCode.NOT_FOUND.value

    if args.list:
        _list_dispositions(task_id, db_path)
        return 0

    if args.clear:
        if not args.file or args.line is None:
            print("--clear requires FILE and LINE.", file=sys.stderr)
            return ExitCode.USAGE_ERROR.value
        if delete_wontfix_entry(task_id, args.file, args.line, db_path):
            print(f"Cleared: {args.file}:{args.line}")
        else:
            print(f"No entry found: {args.file}:{args.line}")
            return ExitCode.NOT_FOUND.value
        return 0

    if not args.file or args.line is None:
        print(
            "Usage: disposition FILE LINE --reason TEXT [--needshuman|--fixed] | --list | --clear FILE LINE",
            file=sys.stderr,
        )
        return ExitCode.USAGE_ERROR.value

    if not args.reason:
        print("Requires --reason.", file=sys.stderr)
        return ExitCode.USAGE_ERROR.value

    if args.fixed:
        disposition = DispositionType.FIXED
    elif args.needshuman:
        disposition = DispositionType.NEEDSHUMAN
    else:
        disposition = DispositionType.WONTFIX

    if not add_wontfix_entry(task_id, args.file, args.line, args.reason, db_path, disposition):
        print(f"Already exists: {args.file}:{args.line}")
        return 0

    print(f"Added {disposition}: {args.file}:{args.line}")
    if disposition == DispositionType.NEEDSHUMAN:
        return _block_task(db_path, task_id, args.file, args.line, args.reason)
    return 0
