"""ft work inbox - Show blocked workers awaiting human input.

Workers use `ft work blocked "question"` to signal they need help.
This command lists them for the supervisor skill or human triage.
"""

import argparse
import json

from formaltask.cli.context import CLIContext, with_repository
from formaltask.workers.inbox import get_blocked_workers


def setup_parser(subparser):
    """Set up argument parser for inbox command."""
    subparser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (for supervisor skill)",
    )
    subparser.add_argument(
        "--db-path",
        default=None,
        help="Database path (default: auto-detect)",
    )


@with_repository
def execute(ctx: CLIContext, args: argparse.Namespace) -> int:
    """Execute the inbox command."""
    workers = get_blocked_workers(ctx.db_path)

    if args.json:
        print(json.dumps(workers, indent=2))
        return 0

    if not workers:
        print("No blocked workers.")
        return 0

    print(f"Blocked workers: {len(workers)}\n")
    for w in workers:
        age = w.get("age_seconds")
        age_str = f"{age // 60}m" if age else "?"
        print(f"  #{w['task_id']} ({age_str} ago): {w['task_title']}")
        print(f"    Q: {w['pending_question']}")
        print()

    print("Resume with: ft work resume <id> -m 'response'")
    return 0
