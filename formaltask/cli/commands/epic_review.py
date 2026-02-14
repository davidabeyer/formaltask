"""pm-epic-review command - Run comprehensive epic-level code review."""

import argparse
import json
import sys

from formaltask.cli.context import CLIContext, with_repository
from formaltask.db.connection import DatabaseConnection
from formaltask.epics import get_epic_status, mark_reviewed
from formaltask.utils.constants import FindingPriority


def _count_findings(findings_json: str) -> tuple[int, int, int]:
    """Count P0, P1, P2 findings from JSON string. Returns (p0, p1, p2) counts."""
    try:
        findings_data = json.loads(findings_json)
    except json.JSONDecodeError:
        return (0, 0, 0)

    # Handle {"findings": [...]} or direct list format
    if isinstance(findings_data, dict) and "findings" in findings_data:
        findings = findings_data["findings"]
    elif isinstance(findings_data, list):
        findings = findings_data
    else:
        return (0, 0, 0)

    p0, p1, p2 = 0, 0, 0
    for finding in findings:
        if isinstance(finding, dict):
            priority = finding.get("priority", "")
            if priority == FindingPriority.P0:
                p0 += 1
            elif priority == FindingPriority.P1:
                p1 += 1
            elif priority == FindingPriority.P2:
                p2 += 1
    return (p0, p1, p2)


def epic_review(epic_name: str, db_path: str) -> dict:
    """Run comprehensive epic-level code review.

    Args:
        epic_name: Name of epic to review
        db_path: Path to database file

    Returns:
        Dict with ready_to_merge, p0_count, p1_count, p2_count, total_tasks, completed_tasks
    """
    status = get_epic_status(db_path, epic_name)

    p0_count, p1_count, p2_count = 0, 0, 0

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            WITH ranked AS (
                SELECT r.findings, t.id,
                       ROW_NUMBER() OVER (PARTITION BY t.id ORDER BY r.round DESC) as rn
                FROM task_reviews r
                JOIN tasks t ON r.task_id = t.id
                WHERE t.epic_name = ? AND t.status = 'completed'
            )
            SELECT findings FROM ranked WHERE rn = 1
        """,
            (epic_name,),
        )

        for (findings_json,) in cursor.fetchall():
            if findings_json:
                p0, p1, p2 = _count_findings(findings_json)
                p0_count += p0
                p1_count += p1
                p2_count += p2

    return {
        "ready_to_merge": p0_count == 0,
        "p0_count": p0_count,
        "p1_count": p1_count,
        "p2_count": p2_count,
        "total_tasks": status["total_tasks"],
        "completed_tasks": status["completed"],
    }


def setup_parser(subparser):
    """Set up argument parser for epic-review command."""
    subparser.add_argument("epic_name", help="Epic name")
    subparser.add_argument(
        "--db-path",
        default=None,
        help="Path to database (default: auto-detect)",
    )


@with_repository
def execute(ctx: CLIContext, args: argparse.Namespace) -> int:
    """Execute the epic-review command."""
    try:
        result = epic_review(epic_name=args.epic_name, db_path=ctx.db_path)
    except (ValueError, KeyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if result["ready_to_merge"]:
        mark_reviewed(ctx.db_path, args.epic_name)
        print(f"✓ Epic '{args.epic_name}' is ready to merge")
        print(f"  Tasks: {result['completed_tasks']}/{result['total_tasks']} completed")
        return 0
    print(f"✗ Epic '{args.epic_name}' is NOT ready to merge")
    print(f"  P0: {result['p0_count']}, P1: {result['p1_count']}, P2: {result['p2_count']}")
    print(f"  Tasks: {result['completed_tasks']}/{result['total_tasks']} completed")
    return 1
