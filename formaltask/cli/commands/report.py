"""ft work report — report an issue for another worker to fix.

Workers use this to create fix tasks for infrastructure problems (CI broken,
missing dependencies, etc.) without blocking themselves. The worker continues
working; the new task enters the spawn queue for another worker to pick up.

Flow: Worker runs ft work report "Fix CI" -> creates task with
task_type=blocker, required_reviews=["self-critique"] -> watch daemon
picks it up -> spawns worker to fix it.

Dedup: Only one open blocker task per epic. First reporter wins.
Rate limit: Max 3 created tasks per source task.
"""

import argparse
import sys

from formaltask.cli.exit_codes import ExitCode
from formaltask.db.connection import DatabaseConnection
from formaltask.db.path import get_db_path
from formaltask.tasks.crud import create_task, get_task
from formaltask.workers.context import get_task_id_from_session

MAX_TASKS_PER_SOURCE = 3


def setup_parser(subparser: argparse.ArgumentParser) -> None:
    """Set up argument parser for report command."""
    subparser.add_argument(
        "title",
        help="Title for the fix task (e.g. 'Fix CI: pytest failures in test_auth')",
    )
    subparser.add_argument(
        "--description",
        help="Additional context about the problem",
    )
    subparser.add_argument(
        "--epic",
        help="Epic name (auto-detected from worker context if omitted)",
    )
    subparser.add_argument(
        "--db-path",
        help="Database path (default: auto-detect)",
    )


def execute(args: argparse.Namespace) -> int:
    """Execute the report command."""
    db_path = str(getattr(args, "db_path", None) or get_db_path())

    # Validate title
    if not args.title.strip():
        print("Error: title cannot be empty", file=sys.stderr)
        return ExitCode.VALIDATION_ERROR.value

    # Require worker context
    source_task_id = get_task_id_from_session()
    if source_task_id is None:
        print("No task context. Run from a worker session.", file=sys.stderr)
        return ExitCode.NOT_FOUND.value

    # Resolve epic from args or worker context
    epic_name = args.epic
    if not epic_name:
        source_task = get_task(db_path, source_task_id)
        if source_task:
            epic_name = source_task["epic_name"]
    if not epic_name:
        print("Error: --epic required (or run from worker context)", file=sys.stderr)
        return ExitCode.VALIDATION_ERROR.value

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()

        # Dedup: check for existing open blocker in same epic
        cursor.execute(
            """SELECT id, title FROM tasks
               WHERE epic_name = ?
               AND json_extract(metadata, '$.task_type') = 'blocker'
               AND status NOT IN ('completed', 'cancelled')
               LIMIT 1""",
            (epic_name,),
        )
        existing = cursor.fetchone()
        if existing:
            print(f"Blocker task #{existing[0]} already exists: {existing[1]}")
            print("Continuing with your current task.")
            return 0

        # Rate limit: max tasks per source task
        cursor.execute(
            """SELECT COUNT(*) FROM tasks
               WHERE json_extract(metadata, '$.source_task_id') = ?""",
            (source_task_id,),
        )
        count = cursor.fetchone()[0]
        if count >= MAX_TASKS_PER_SOURCE:
            print(
                f"Error: Task #{source_task_id} already created {count} tasks (max {MAX_TASKS_PER_SOURCE})",
                file=sys.stderr,
            )
            return ExitCode.VALIDATION_ERROR.value

    # Build description
    description = args.description or f"Reported by worker on task #{source_task_id}"

    # Create the blocker task
    task_id = create_task(
        db_path=db_path,
        epic_name=epic_name,
        title=args.title.strip(),
        description=description,
        criteria=[f"Resolve: {args.title.strip()}"],
        metadata={
            "task_type": "blocker",
            "required_reviews": ["self-critique"],
            "source_task_id": source_task_id,
            "completion_rules": [
                {
                    "when": "blocking_findings AND review_rounds.self-critique >= 2",
                    "then": "needs_escalation",
                    "target": "task.phase",
                    "priority": 1,
                    "name": "Blocker task failed self-critique twice. Run: ft work blocked 'findings persist'",
                }
            ],
        },
    )

    print(f"Created blocker task #{task_id}: {args.title.strip()}")
    print("You can continue working. Another worker will pick this up.")
    return 0
