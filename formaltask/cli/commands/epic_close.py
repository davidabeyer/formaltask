"""epic-close command - Archive an epic when all tasks are complete."""

import shutil
from datetime import datetime
from pathlib import Path

from formaltask.cli.base import CLIError
from formaltask.cli.context import with_db_path
from formaltask.cli.exit_codes import ExitCode
from formaltask.epics import archive_epic, get_epic
from formaltask.paths import get_projects_dir


def _archive_project_dir(epic_name: str, projects_dir: str) -> str | None:
    """Move project dir to Archive/. Returns new path or None."""
    base_path = Path(projects_dir).resolve()
    project_path = (Path(projects_dir) / epic_name).resolve()
    if not project_path.is_relative_to(base_path):
        raise ValueError(f"Invalid epic name: path traversal detected in '{epic_name}'")
    if not project_path.exists():
        return None

    archive_path = Path(projects_dir) / "Archive" / epic_name
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        archive_path = Path(projects_dir) / "Archive" / f"{epic_name}_{timestamp}"

    shutil.move(str(project_path), str(archive_path))
    return str(archive_path)


def epic_close(
    epic_name: str, db_path: str, force: bool = False, projects_dir: str | None = None
) -> dict:
    """Archive an epic. Optionally move its project directory to Archive/."""
    if not get_epic(db_path, epic_name):
        raise CLIError(f"Epic '{epic_name}' not found", exit_code=ExitCode.NOT_FOUND)

    archive_epic(db_path, epic_name, force=force)
    result = {
        "epic_name": epic_name,
        "status": "archived",
        "project_moved": False,
        "moved_to": None,
    }

    if projects_dir:
        moved_to = _archive_project_dir(epic_name, projects_dir)
        if moved_to:
            result["project_moved"] = True
            result["moved_to"] = moved_to

    return result


def setup_parser(subparser):
    """Set up argument parser for epic-close command."""
    subparser.add_argument("epic_name", help="Name of the epic to archive")
    subparser.add_argument(
        "--force", action="store_true", help="Archive even with incomplete tasks"
    )
    subparser.add_argument(
        "--db-path", default=None, help="Path to database (default: auto-detect)"
    )
    subparser.add_argument(
        "--projects-dir",
        default=str(get_projects_dir()),
        help="Projects directory (default: ~/projects)",
    )


@with_db_path
def execute(db_path: str, args) -> int:
    """Execute the epic-close command."""
    import json as json_module
    import sys

    json_mode = getattr(args, "json", False)
    try:
        result = epic_close(
            args.epic_name,
            db_path=db_path,
            force=getattr(args, "force", False),
            projects_dir=getattr(args, "projects_dir", None),
        )
        if json_mode:
            print(json_module.dumps({"success": True, "data": result}))
        elif result.get("project_moved"):
            print(f"✓ Archived epic '{args.epic_name}' and moved project to {result['moved_to']}")
        else:
            print(f"✓ Archived epic '{args.epic_name}'")
        return 0
    except (CLIError, ValueError) as e:
        if json_mode:
            print(json_module.dumps({"success": False, "error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        if isinstance(e, CLIError):
            return e.exit_code.value if hasattr(e.exit_code, "value") else e.exit_code
        return ExitCode.NOT_FOUND.value
