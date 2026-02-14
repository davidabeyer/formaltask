"""pm-epic-update command - Update epic attributes after creation."""

from datetime import UTC

from formaltask.cli.context import with_db_path
from formaltask.epics.repository import EpicRepository


def epic_update(
    epic_name,
    db_path: str,
    feature_branch=None,
    description=None,
    unarchive=False,
    reviewed_at=None,
):
    """Update an epic's attributes.

    Args:
        epic_name: Name of epic to update
        db_path: Path to the database
        feature_branch: New feature branch name (optional)
        description: New description (optional)
        unarchive: If True, unarchive the epic (clear archived_at)
        reviewed_at: ISO timestamp to mark epic as reviewed (optional)

    Returns:
        dict with epic_name and updated attributes

    Raises:
        ValueError: If epic not found
    """
    epic_ops = EpicRepository(db_path)
    if unarchive:
        epic_ops.unarchive_epic(epic_name)
    else:
        epic_ops.update_epic(
            epic_name,
            description=description,
            feature_branch=feature_branch,
            reviewed_at=reviewed_at,
        )
    epic = epic_ops.get_epic(epic_name)
    return {"epic_name": epic_name, "feature_branch": epic["feature_branch"]}


def setup_parser(subparser):
    """Set up argument parser for epic-update command."""
    subparser.add_argument("epic_name", help="Name of the epic to update")
    subparser.add_argument("--feature-branch", help="Set the feature branch")
    subparser.add_argument("--description", help="Update the epic description")
    subparser.add_argument(
        "--reviewed", action="store_true", help="Mark epic as reviewed (sets reviewed_at)"
    )
    subparser.add_argument(
        "--unarchive", action="store_true", help="Unarchive a previously closed epic"
    )
    subparser.add_argument("--db-path", help="Path to database")


@with_db_path
def execute(db_path: str, args) -> int:
    """Execute the epic-update command."""
    import sys
    from datetime import datetime

    try:
        unarchive = getattr(args, "unarchive", False)
        feature_branch = getattr(args, "feature_branch", None)
        description = getattr(args, "description", None)
        reviewed = getattr(args, "reviewed", False)

        # Validate --unarchive is used alone
        if unarchive and (feature_branch or description or reviewed):
            print(
                "Warning: --unarchive ignores other flags",
                file=sys.stderr,
            )

        reviewed_at = datetime.now(UTC).isoformat() if reviewed else None

        epic_update(
            args.epic_name,
            db_path=db_path,
            feature_branch=feature_branch,
            description=description,
            unarchive=unarchive,
            reviewed_at=reviewed_at,
        )
        if unarchive:
            print(f"Unarchived epic '{args.epic_name}'")
        elif reviewed:
            print(f"Marked epic '{args.epic_name}' as reviewed")
        else:
            print(f"Updated epic '{args.epic_name}'")
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
