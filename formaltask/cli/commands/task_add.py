"""pm-task-add command - Add new task to an epic.

Issue #1066: Added compensating transaction with verified deletion.
"""

import argparse
import json
import logging
import sys
from collections.abc import Callable

from formaltask.cli.base import CLIError
from formaltask.cli.context import CLIContext, with_repository
from formaltask.cli.exit_codes import ExitCode
from formaltask.cli.output import OutputFormatter
from formaltask.epics import get_epic
from formaltask.exceptions import EpicNotFoundError
from formaltask.tasks.crud import create_task, delete_task_verified
from formaltask.utils.template_loader import merge_template

logger = logging.getLogger(__name__)


class TaskAddError(Exception):
    """Error during task addition with compensating transaction."""


def task_add(
    epic_name: str,
    title: str,
    description: str,
    criteria: list[str],
    db_path: str,
    depends_on: list[int] | None = None,
    metadata: dict | None = None,
    status: str | None = None,
    post_create_callback: Callable[[int], None] | None = None,
    due_date: str | None = None,
    priority: int | None = None,
) -> int:
    """Add a new task to an epic.

    Args:
        epic_name: Epic to add task to
        title: Task title
        description: Task description
        criteria: List of acceptance criteria
        db_path: Path to SQLite database
        depends_on: List of task IDs this task depends on (optional)
        metadata: Optional JSON metadata including artifact_type and artifact_content
        status: Initial task status (default: 'open', use 'blocked' for critique-first workflow)
        post_create_callback: Optional callback to run after task creation.
            If this fails, the task is deleted (compensating transaction).
        due_date: Optional due date in YYYY-MM-DD format
        priority: Optional priority level (1=highest)

    Returns:
        Task ID of created task

    Raises:
        TaskAddError: If post_create_callback fails (with original exception chained)
    """
    # Create task in database
    task_id = create_task(
        db_path=db_path,
        epic_name=epic_name,
        title=title,
        description=description,
        criteria=criteria,
        depends_on=depends_on,
        metadata=metadata,
        status=status,
        due_date=due_date,
        priority=priority,
    )

    # Run post-creation callback if provided
    if post_create_callback is not None:
        try:
            post_create_callback(task_id)
        except Exception as e:
            # Compensating transaction: delete the task with verification
            logger.error(
                f"Post-create callback failed for task #{task_id}: {e}",
                exc_info=True,
            )
            try:
                deleted = delete_task_verified(db_path, task_id)
                if not deleted:
                    logger.error(
                        f"Compensating transaction failed: could not delete task #{task_id}"
                    )
            except Exception as delete_error:
                # Log delete failure but preserve original exception chain
                logger.error(
                    f"Compensating transaction raised exception for task #{task_id}: "
                    f"{delete_error}",
                    exc_info=True,
                )
            raise TaskAddError(f"Failed to complete task creation for task #{task_id}") from e

    return int(task_id)


SUPPORTS_PREFLIGHT = True
SUPPORTS_DRY_RUN = True


def setup_parser(subparser: argparse.ArgumentParser) -> None:
    """Set up argument parser for task-add command."""
    subparser.add_argument("epic_name", help="Epic to add task to")
    subparser.add_argument("title", help="Task title")
    subparser.add_argument("description", help="Task description")
    subparser.add_argument(
        "--criteria",
        action="append",
        required=True,
        dest="criteria",
        help="Acceptance criteria (use multiple --criteria flags)",
    )
    subparser.add_argument(
        "--depends-on",
        action="append",
        type=int,
        dest="depends_on",
        help="Task ID this task depends on (use multiple --depends-on flags)",
    )
    subparser.add_argument(
        "--db-path",
        default=None,
        help="Path to database (default: auto-detect)",
    )
    subparser.add_argument(
        "--metadata",
        type=str,
        dest="metadata_json",
        help="JSON metadata including artifact_type and artifact_content",
    )
    subparser.add_argument(
        "--status",
        type=str,
        choices=["open", "blocked"],
        default="open",
        help="Initial task status (default: open, use blocked for critique-first workflow)",
    )
    subparser.add_argument(
        "--label",
        action="append",
        dest="labels",
        help="Add label to task metadata (use multiple --label flags)",
    )
    subparser.add_argument(
        "--due-date",
        type=str,
        dest="due_date",
        help="Due date (YYYY-MM-DD format)",
    )
    subparser.add_argument(
        "--priority",
        type=int,
        dest="priority",
        help="Priority level (1=highest)",
    )
    subparser.add_argument(
        "--template",
        "-t",
        type=str,
        default="implementation",
        help="Task template name (default: implementation)",
    )
    subparser.add_argument(
        "--spec-review",
        action="store_true",
        help="Use spec-review template (shortcut for --template spec-review)",
    )
    subparser.add_argument(
        "--epic-review",
        action="store_true",
        help="Use epic-review template (shortcut for --template epic-review)",
    )


def _get_template_name(args: argparse.Namespace) -> str:
    """Get template name from args, with shortcuts taking precedence."""
    if getattr(args, "spec_review", False):
        return "spec-review"
    if getattr(args, "epic_review", False):
        return "epic-review"
    return getattr(args, "template", "implementation")


@with_repository
def execute(ctx: CLIContext, args: argparse.Namespace) -> int:
    """Execute the task-add command."""
    formatter = OutputFormatter(args)

    # Determine template name
    template_name = _get_template_name(args)

    # Preflight mode
    if getattr(args, "preflight", False):
        epic = get_epic(ctx.db_path, args.epic_name)
        if epic:
            data = {"preflight": {"can_proceed": True, "blockers": []}}
        else:
            data = {
                "preflight": {
                    "can_proceed": False,
                    "blockers": [f"Epic '{args.epic_name}' not found"],
                }
            }
        print(formatter.success(data, "Preflight check complete"))
        return 0

    # Dry-run mode
    if getattr(args, "dry_run", False):
        epic = get_epic(ctx.db_path, args.epic_name)
        # Get metadata from template for dry-run preview
        explicit_metadata = {}
        if args.metadata_json:
            explicit_metadata = json.loads(args.metadata_json)
        merged_metadata = merge_template(template_name, explicit_metadata)
        if epic:
            data = {
                "dry_run": {
                    "side_effects": [
                        f"Would create task '{args.title}' in epic '{args.epic_name}'"
                    ],
                    "template": template_name,
                    "metadata": merged_metadata,
                }
            }
        else:
            data = {
                "dry_run": {"blockers": [f"Epic '{args.epic_name}' not found"], "side_effects": []}
            }
        print(formatter.success(data, "Dry-run preview"))
        return 0

    try:
        # Parse explicit metadata JSON if provided
        explicit_metadata = {}
        if args.metadata_json:
            explicit_metadata = json.loads(args.metadata_json)
            if not isinstance(explicit_metadata, dict):
                print(
                    "Error: Metadata must be a JSON object, not an array or primitive",
                    file=sys.stderr,
                )
                return 1

        # Merge labels into metadata
        if getattr(args, "labels", None):
            existing_labels = explicit_metadata.get("labels", [])
            explicit_metadata["labels"] = existing_labels + args.labels

        # Merge template defaults with explicit metadata
        metadata = merge_template(template_name, explicit_metadata)

        # Handle due_date and priority as direct column values
        due_date = getattr(args, "due_date", None)
        priority = getattr(args, "priority", None)

        task_id = task_add(
            epic_name=args.epic_name,
            title=args.title,
            description=args.description,
            criteria=args.criteria,
            db_path=ctx.db_path,
            depends_on=args.depends_on,
            metadata=metadata if metadata else None,
            status=args.status,
            due_date=due_date,
            priority=priority,
        )

        result_data = {"task_id": task_id, "epic_name": args.epic_name}
        print(formatter.success(result_data, "✓ Added task #{task_id}"))
        return 0

    except json.JSONDecodeError as e:
        print(f"Error: Invalid metadata JSON: {e}", file=sys.stderr)
        return 1
    except CLIError as e:
        print(f"Error: {e.message}", file=sys.stderr)
        return int(e.exit_code)
    except EpicNotFoundError as e:
        error = CLIError(str(e), exit_code=ExitCode.NOT_FOUND)
        print(formatter.error(error))
        return int(ExitCode.NOT_FOUND)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1
