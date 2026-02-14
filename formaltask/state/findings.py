"""Findings state query logic for task disposition analysis."""

import logging
from dataclasses import dataclass
from pathlib import Path

from formaltask.utils.constants import DispositionType, FindingPriority

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FindingsState:
    """Immutable snapshot of task findings state."""

    has_reviews: bool
    has_wontfix: bool
    has_needshuman_critical: bool
    has_needshuman_deferrable: bool
    has_unresolved_findings: bool
    latest_review_clean: bool


def check_findings_state(task_id: int, db_path: str | Path) -> FindingsState:
    """Derive findings state from get_findings_with_disposition + review metadata."""
    from formaltask.db.connection import DatabaseConnection

    findings = get_findings_with_disposition(task_id, db_path)

    has_wontfix = has_critical = has_deferrable = has_unresolved = False
    for f in findings:
        d = f["disposition"]
        if d is None:
            has_unresolved = True
        elif d == DispositionType.WONTFIX:
            has_wontfix = True
        elif d == DispositionType.NEEDSHUMAN:
            if f["priority"] in (FindingPriority.P0, FindingPriority.P1):
                has_critical = True
            else:
                has_deferrable = True

    # Review metadata — not derivable from findings list
    db_path = Path(db_path) if isinstance(db_path, str) else db_path
    with DatabaseConnection(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT severity FROM task_reviews
               WHERE task_id = ? AND ignored = 0
               ORDER BY round DESC LIMIT 1""",
            (task_id,),
        )
        row = cursor.fetchone()

    return FindingsState(
        has_reviews=row is not None,
        has_wontfix=has_wontfix,
        has_needshuman_critical=has_critical,
        has_needshuman_deferrable=has_deferrable,
        has_unresolved_findings=has_unresolved,
        latest_review_clean=row is not None and row[0] == "clean",
    )


def get_findings_with_disposition(task_id: int, db_path: str | Path) -> list[dict]:
    """Query individual findings for a task with disposition status.

    Task #2598: Returns findings from LATEST round per review_type only,
    fixing the stale findings bug where old round findings persisted.

    Args:
        task_id: The task ID to query findings for.
        db_path: Path to the SQLite database.

    Returns:
        List of dicts with keys: file, line, priority, description, disposition.
        Returns empty list if no reviews or no findings exist.
    """
    import json

    from formaltask.db.connection import DatabaseConnection

    db_path = Path(db_path) if isinstance(db_path, str) else db_path

    with DatabaseConnection(str(db_path)) as conn:
        cursor = conn.cursor()
        # Task #2598: Get only latest round per review_type (fixes stale findings bug)
        cursor.execute(
            """SELECT findings FROM task_reviews
               WHERE task_id = ? AND ignored = 0
               AND (review_type, round) IN (
                   SELECT review_type, MAX(round)
                   FROM task_reviews
                   WHERE task_id = ? AND ignored = 0
                   GROUP BY review_type
               )""",
            (task_id, task_id),
        )
        rows = cursor.fetchall()
        if not rows:
            return []

        # Query finding_dispositions to build dict of (file, line) -> disposition
        cursor.execute(
            "SELECT file, line, disposition FROM finding_dispositions WHERE task_id = ?",
            (task_id,),
        )
        dispositions = {(r[0], r[1]): r[2] for r in cursor.fetchall()}

        # Aggregate findings from all reviews, deduplicating by (file, line)
        seen = set()
        result = []
        for row in rows:
            if not row[0]:
                continue
            try:
                findings = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            except json.JSONDecodeError:
                continue

            # Handle nested dict structure: {"findings": [...], "summary": "..."}
            if isinstance(findings, dict) and "findings" in findings:
                findings = findings["findings"]

            for f in findings:
                file_path = f.get("file", "")
                line_num = f.get("line", 0)
                key = (file_path, line_num)
                if key in seen:
                    continue  # Skip duplicate findings
                seen.add(key)

                disp = dispositions.get(key)
                result.append(
                    {
                        "file": file_path,
                        "line": line_num,
                        "priority": f.get("priority") or f.get("severity", ""),
                        "description": f.get("description", ""),
                        "disposition": disp if disp else None,
                    }
                )
        return result
