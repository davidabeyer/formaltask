"""epic-decompose command — Create tasks from epic spec directory."""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from pydantic import ValidationError

from formaltask.cli.context import with_db_path
from formaltask.db.connection import DatabaseConnection
from formaltask.db.helpers import transaction
from formaltask.epics.yaml_parser import (
    SpecFormatError,
    parse_specs_dir,
    validate_task_quality,
)
from formaltask.paths import get_projects_dir
from formaltask.tasks.crud import create_tasks_batch
from formaltask.tasks.dependencies import has_circular_dependencies
from formaltask.utils.schemas import TaskTitle
from formaltask.validators.file_conflict import detect_file_conflicts

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(
    os.getenv("PROJECT_ROOT", Path(__file__).parent.parent.parent.parent)
).resolve()


def _cleanup_tasks(db_path: str, task_ids: list[int]) -> None:
    """Atomically delete tasks and their acceptance criteria."""
    if not task_ids:
        return
    with DatabaseConnection(db_path) as conn, transaction(conn):
        ph = ",".join("?" * len(task_ids))
        # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
        conn.execute(f"DELETE FROM acceptance_criteria WHERE task_id IN ({ph})", task_ids)
        # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
        conn.execute(f"DELETE FROM tasks WHERE id IN ({ph})", task_ids)


def epic_decompose(
    epic_name: str,
    spec_dir_path: str,
    db_path: str | None = None,
    strict: bool = False,
    force: bool = False,
) -> list[int]:
    """Decompose epic spec directory into database tasks.

    Args:
        epic_name: Name of the epic in the database.
        spec_dir_path: Path to spec directory containing task-*.yaml files.
        db_path: Path to the database.
        strict: If True, reject tasks with quality warnings.
        force: If True, delete existing tasks and re-decompose.
    """
    if db_path is None:
        raise ValueError("db_path is required")

    # --- Validate spec directory path ---
    resolved = Path(spec_dir_path).resolve()
    allowed_roots = [
        get_projects_dir(),
        Path.home() / "Projects",
        _PROJECT_ROOT,
    ]
    if not any(resolved.is_relative_to(r) for r in allowed_roots):
        raise ValueError(f"Path outside allowed directories: {spec_dir_path}")

    if not resolved.is_dir():
        raise ValueError(f"Spec directory not found: {spec_dir_path}")

    # --- Ensure epic exists in DB ---
    with DatabaseConnection(db_path) as conn:
        row = conn.execute("SELECT name FROM epics WHERE name = ?", (epic_name,)).fetchone()
        if row is None:
            raise ValueError(f"Epic '{epic_name}' not found. Run: ft epic create {epic_name}")

    # --- Idempotency: check existing tasks ---
    with DatabaseConnection(db_path) as conn:
        existing = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE epic_name = ?", (epic_name,)
        ).fetchone()[0]
    if existing > 0:
        if not force:
            raise ValueError(
                f"Epic '{epic_name}' already has {existing} tasks. "
                f"Use force=True to delete existing tasks and re-decompose."
            )
        with DatabaseConnection(db_path) as conn:
            rows = conn.execute("SELECT id FROM tasks WHERE epic_name = ?", (epic_name,)).fetchall()
            _cleanup_tasks(db_path, [r[0] for r in rows])

    # --- Parse spec directory ---
    try:
        tasks = parse_specs_dir(str(resolved))
    except SpecFormatError as e:
        raise ValueError(f"Spec directory parsing failed: {e}") from e

    validation = validate_task_quality(tasks)
    if strict and (validation.warnings or validation.errors):
        raise ValueError(f"Task quality validation failed:\n{validation}")

    # --- Build batch task data ---
    batch_tasks = []
    for task in tasks:
        spec_content = task.get("spec_content")
        if not spec_content and not task.get("criteria"):
            raise ValueError(
                f"Task '{task.get('title', 'Unknown')}' has no spec_content and no criteria."
            )

        # Build metadata
        metadata: dict = {}
        if spec_content:
            metadata["artifact_type"] = "spec"
            metadata["artifact_content"] = spec_content
        if task.get("required_reviews") is not None:
            metadata["required_reviews"] = task["required_reviews"]
        if task.get("skills"):
            metadata["skills"] = task["skills"]
        if task.get("documentation_required") is not None:
            metadata["documentation_required"] = task["documentation_required"]
        if task.get("inputs"):
            metadata["inputs"] = task["inputs"]
        if task.get("outputs"):
            metadata["outputs"] = task["outputs"]
        if task.get("prompt_template"):
            metadata["prompt_template"] = task["prompt_template"]

        if task.get("required_reviews"):
            logger.info(
                "Task '%s' has required reviews: %s",
                task.get("title", "Unknown"),
                ", ".join(task["required_reviews"]),
            )

        full_title = f"{epic_name}: {task['title']}"
        try:
            TaskTitle(value=full_title, epic_name=epic_name)
        except ValidationError as e:
            raise ValueError(f"Invalid task title '{full_title}': {e.errors()[0]['msg']}") from e

        batch_task = {
            "title": full_title,
            "description": task["description"],
            "criteria": task.get("criteria", []),
            "metadata": metadata or None,
        }

        # Convert depends_on (0-based positions) to depends_on_positions for create_tasks_batch
        deps = task.get("depends_on", [])
        if deps:
            batch_task["depends_on_positions"] = deps

        batch_tasks.append(batch_task)

    # --- Create tasks with dependency resolution ---
    task_ids = create_tasks_batch(db_path, epic_name, batch_tasks)
    if has_circular_dependencies(db_path, epic_name):
        _cleanup_tasks(db_path, task_ids)
        raise ValueError("Circular dependencies detected in epic decomposition")

    # --- Advisory: detect file conflicts ---
    with DatabaseConnection(db_path) as conn:
        ph = ",".join("?" * len(task_ids))
        # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
        rows = conn.execute(
            f"SELECT id, metadata FROM tasks WHERE id IN ({ph})", task_ids
        ).fetchall()
        specs = []
        for row in rows:
            spec = ""
            if row[1]:
                try:
                    spec = json.loads(row[1]).get("artifact_content", "")
                except (json.JSONDecodeError, AttributeError):
                    pass
            specs.append({"id": row[0], "spec_content": spec})
    conflicts = detect_file_conflicts(
        specs
    )  # Returns list[tuple[str, list[int]]] when check_deps=False
    for path, ids in conflicts:  # type: ignore[misc]
        logger.warning("File conflict: '%s' modified by tasks %s", path, ids)

    return task_ids


def epic_validate(epic_name: str, db_path: str) -> dict:
    """Validate an epic without creating tasks."""
    from formaltask.epics.validation import epic_finalize

    return epic_finalize(epic_name, db_path)


def setup_parser(subparser):
    """Set up argument parser for epic-decompose command."""
    subparser.add_argument("epic_name", help="Epic name")
    subparser.add_argument("spec_dir", help="Path to spec directory containing task-*.yaml files")
    subparser.add_argument(
        "--db-path", default=None, help="Path to database (default: auto-detect)"
    )
    subparser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing tasks and re-decompose (GitHub issues NOT deleted)",
    )
    subparser.add_argument(
        "--validate",
        action="store_true",
        help="Validate existing tasks only (don't create new tasks)",
    )


@with_db_path
def execute(db_path: str, args: argparse.Namespace) -> int:
    """Execute the epic-decompose command."""
    if getattr(args, "validate", False):
        try:
            result = epic_validate(args.epic_name, db_path=db_path)
        except (ValueError, SpecFormatError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        print(f"\nEpic: {args.epic_name}")
        print(f"Tasks validated: {result.get('tasks_validated', 0)}")
        if result.get("validation_errors"):
            print("\nErrors:")
            for error in result["validation_errors"]:
                print(f"  - {error}")
        if result.get("quality_warnings"):
            print("\nWarnings:")
            for warning in result["quality_warnings"]:
                print(f"  - {warning}")
        if result["ready_for_sync"]:
            print("\n✓ Validation passed")
            return 0
        print("\n✗ Validation failed")
        return 1

    try:
        task_ids = epic_decompose(
            epic_name=args.epic_name,
            spec_dir_path=args.spec_dir,
            db_path=db_path,
            force=getattr(args, "force", False),
        )
    except (ValueError, SpecFormatError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    from formaltask.epics.planning import begin_stage

    begin_stage(args.epic_name, "epic-decompose", db_path)

    print(f"✓ Created {len(task_ids)} tasks from epic '{args.epic_name}'")
    print(f"  Task IDs: {', '.join(f'#{tid}' for tid in task_ids)}")

    return 0
