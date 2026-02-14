"""pm-epic-create command - Create a new epic."""

import argparse
import json as json_module
import sys

from formaltask.cli.base import CLIError
from formaltask.cli.context import with_db_path
from formaltask.cli.exit_codes import ExitCode
from formaltask.epics import create_epic as _create_epic


def epic_create(epic_name, description, db_path: str, skip_review=False):
    """Create a new epic.

    Returns:
        dict: {"epic_name": ..., "created": True}
    """
    _create_epic(
        db_path=db_path,
        name=epic_name,
        description=description,
        skip_review=skip_review,
    )
    return {"epic_name": epic_name, "created": True}


def setup_parser(subparser):
    """Set up argument parser for epic-create command."""
    subparser.add_argument(
        "epic_name",
        help="Epic name (kebab-case recommended)",
    )
    subparser.add_argument(
        "description",
        help="Epic description",
    )
    subparser.add_argument(
        "--skip-review",
        action="store_true",
        help="Skip review phase",
    )
    subparser.add_argument(
        "--db-path",
        default=None,
        help="Path to database (default: auto-detect)",
    )


@with_db_path
def execute(db_path: str, args: argparse.Namespace) -> int:
    """Execute the epic-create command."""
    json_mode = getattr(args, "json", False)

    try:
        result = epic_create(
            epic_name=args.epic_name,
            description=args.description,
            db_path=db_path,
            skip_review=getattr(args, "skip_review", False),
        )

        if json_mode:
            print(json_module.dumps({"success": True, "data": result}))
        else:
            print(f"✓ Created epic: {args.epic_name}")

        return 0

    except CLIError as e:
        if json_mode:
            print(json_module.dumps({"success": False, "error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return e.exit_code.value if hasattr(e.exit_code, "value") else e.exit_code

    except ValueError as e:
        if json_mode:
            print(json_module.dumps({"success": False, "error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return ExitCode.CONFLICT.value
