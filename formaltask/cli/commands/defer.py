"""ft defer command - Create new task from review finding (Task #2890).

Workers use this to create new tasks from review findings with provenance tracking.
Unlike task-defer which DEFERS existing tasks, this command CREATES new tasks.

Flow: Worker runs ft defer src/foo.py 42 --title "Fix edge case" -> creates task with
metadata {finding_ref, task_type, required_reviews, source_task_id} ->
watch daemon picks it up via get_spawnable_tasks() -> spawns worker.
"""

import argparse
import sys
from pathlib import Path

from formaltask.cli.exit_codes import ExitCode
from formaltask.db.connection import DatabaseConnection
from formaltask.db.path import get_db_path
from formaltask.tasks.crud import create_task, get_task
from formaltask.workers.context import get_task_id_from_session


def setup_parser(subparser: argparse.ArgumentParser) -> None:
    """Set up argument parser for defer command.

    Args:
        subparser: Argument parser to configure.
    """
    subparser.add_argument(
        "file",
        metavar="FILE",
        help="Source file path containing the finding",
    )
    subparser.add_argument(
        "line",
        metavar="LINE",
        type=int,
        help="Line number of the finding",
    )
    subparser.add_argument(
        "--title",
        required=True,
        help="Title for the new task",
    )
    subparser.add_argument(
        "--task-type",
        dest="task_type",
        default="critique-gated",
        help="Task workflow type (default: critique-gated)",
    )
    subparser.add_argument(
        "--epic",
        help="Epic name (auto-detected from .task/id if in worker context)",
    )
    subparser.add_argument(
        "--spawn",
        action="store_true",
        help="Immediately spawn a worker for the created task",
    )
    subparser.add_argument(
        "--db-path",
        help="Database path (default: auto-detect)",
    )


def _resolve_epic_with_task_id(
    args: argparse.Namespace, db_path: str, source_task_id: int | None
) -> str | None:
    """Resolve epic name from args or worker context.

    Args:
        args: Parsed command line arguments.
        db_path: Path to database.
        source_task_id: Task ID from worker context, or None.

    Returns:
        Epic name if resolved, None otherwise.
    """
    # Use explicit --epic if provided
    if args.epic:
        return args.epic

    # Try to detect from worker context
    if source_task_id is not None:
        task = get_task(db_path, source_task_id)
        if task:
            return task["epic_name"]

    return None


def _check_duplicate_finding_ref(db_path: str, finding_ref: str) -> bool:
    """Check if a task with the given finding_ref already exists.

    Args:
        db_path: Path to database.
        finding_ref: Finding reference (file:line).

    Returns:
        True if duplicate exists, False otherwise.
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        # Search for finding_ref in metadata JSON
        cursor.execute(
            """SELECT id FROM tasks
               WHERE json_extract(metadata, '$.finding_ref') = ?""",
            (finding_ref,),
        )
        return cursor.fetchone() is not None


def execute(args: argparse.Namespace) -> int:
    """Execute the defer command.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    db_path = str(getattr(args, "db_path", None) or get_db_path())

    # Validate title is not empty
    if not args.title.strip():
        print("Error: --title cannot be empty", file=sys.stderr)
        return ExitCode.VALIDATION_ERROR.value

    # Validate file exists and normalize path
    file_path = Path(args.file).resolve()
    if not file_path.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return ExitCode.NOT_FOUND.value

    # Validate line number is positive
    if args.line <= 0:
        print(f"Error: Line number must be positive, got: {args.line}", file=sys.stderr)
        return ExitCode.VALIDATION_ERROR.value

    # Construct finding_ref with normalized path
    finding_ref = f"{file_path}:{args.line}"

    # Check for duplicate finding_ref
    if _check_duplicate_finding_ref(db_path, finding_ref):
        print(f"Error: Task with finding_ref '{finding_ref}' already exists", file=sys.stderr)
        return ExitCode.ALREADY_EXISTS.value

    # Get source task id (if in worker context) - used for both epic resolution and metadata
    source_task_id = get_task_id_from_session()

    # Resolve epic
    epic_name = _resolve_epic_with_task_id(args, db_path, source_task_id)
    if not epic_name:
        print("Error: --epic required (or run from worker context)", file=sys.stderr)
        return ExitCode.VALIDATION_ERROR.value

    # Build metadata
    task_type = args.task_type
    metadata = {
        "finding_ref": finding_ref,
        "task_type": task_type,
    }
    if task_type == "critique-gated":
        metadata["required_reviews"] = ["self-critique"]
        metadata["completion_rules"] = [
            {
                "when": "blocking_findings AND review_rounds.self-critique >= 2",
                "then": "needs_escalation",
                "target": "task.phase",
                "priority": 1,
                "name": "Critique round limit. Run: ft work blocked 'P0/P1 findings persist after self-critique'",
            }
        ]
    if source_task_id is not None:
        metadata["source_task_id"] = source_task_id

    # Create task
    task_id = create_task(
        db_path=db_path,
        epic_name=epic_name,
        title=args.title.strip(),
        description=f"Deferred from finding at {finding_ref}",
        criteria=[f"Address finding at {finding_ref}"],
        metadata=metadata,
    )

    print(f"Created task #{task_id} for finding {finding_ref}")

    # Spawn worker if requested
    if args.spawn:
        from formaltask.workers.spawner import spawn_worker

        spawn_worker(task_id, db_path)
        print(f"Spawned worker for task #{task_id}")

    return 0
