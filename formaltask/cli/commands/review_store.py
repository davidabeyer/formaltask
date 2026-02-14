"""pm review-store — store review packet to database."""

import argparse
import json
import sys

from pydantic import ValidationError

from formaltask.cli.base import CLIError
from formaltask.cli.context import with_db_path
from formaltask.cli.exit_codes import ExitCode
from formaltask.db.connection import DatabaseConnection
from formaltask.git.utils import get_head_sha
from formaltask.review.packet_schema import ReviewPacket


def setup_parser(subparser):
    """Set up argument parser for review-store command."""
    subparser.add_argument(
        "review_json",
        nargs="?",
        default=None,
        help="Review JSON (reads from stdin if not provided)",
    )
    subparser.add_argument(
        "--db-path",
        default=None,
        help="Database path (default: auto-detect)",
    )


@with_db_path
def execute(db_path: str, args: argparse.Namespace) -> int:
    """Execute the review-store command."""
    # Read from stdin if no argument provided
    review_json = args.review_json
    if review_json is None:
        review_json = sys.stdin.read().strip()

    result = review_store(review_json, db_path=db_path)
    assert isinstance(result, int)
    return result


def review_store(review_json: str, db_path: str, json_mode: bool = False) -> int | dict:
    """Store a review packet. Returns dict in json_mode, int otherwise."""
    # Parse JSON
    try:
        data = json.loads(review_json)
    except json.JSONDecodeError as e:
        if json_mode:
            raise CLIError(f"Invalid JSON: {e}", exit_code=ExitCode.USAGE_ERROR) from None
        print(f"Error: Invalid JSON: {e}")
        return 1

    # Validate schema
    try:
        packet = ReviewPacket.model_validate(data)
    except ValidationError as e:
        if json_mode:
            raise CLIError(f"Validation error: {e}", exit_code=ExitCode.USAGE_ERROR) from None
        print(f"Error: Validation error: {e}")
        return 1

    # Get HEAD SHA (None if git fails or invalid format)
    sha = get_head_sha()

    # Store to database with exclusive transaction for atomicity
    with DatabaseConnection(db_path, exclusive=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO task_reviews
            (task_id, review_type, round, severity, findings, reviewed_at, reviewed_sha, source)
            VALUES (?, ?,
                (SELECT COALESCE(MAX(round), 0) + 1
                 FROM task_reviews WHERE task_id = ? AND review_type = ?),
                ?, ?, datetime('now'), ?, 'claude')
            """,
            (
                packet.task_id,
                packet.review_type,
                packet.task_id,
                packet.review_type,
                packet.severity,
                json.dumps(packet.findings),
                sha,
            ),
        )

        # Sync tasks.last_review_sha
        cursor.execute(
            "UPDATE tasks SET last_review_sha = ? WHERE id = ?",
            (sha, packet.task_id),
        )
        # Note: No explicit commit needed - DatabaseConnection.__exit__ auto-commits for exclusive=True

    if json_mode:
        return {
            "task_id": packet.task_id,
            "review_type": packet.review_type,
            "stored": True,
        }

    print(f"Review stored: task={packet.task_id}, type={packet.review_type}")
    return 0
