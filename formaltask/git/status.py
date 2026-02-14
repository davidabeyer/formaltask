"""Git and GitHub status utilities."""

import json
import logging
import sqlite3
import subprocess

from formaltask.db.connection import DatabaseConnection
from formaltask.utils.constants import FindingPriority

logger = logging.getLogger(__name__)


def get_reviews_status(task_id: int, db_path: str) -> tuple[int, int]:
    """Get (required_count, completed_count) for task reviews."""
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT metadata FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if not row or not row[0]:
                return (0, 0)
            try:
                metadata = json.loads(row[0])
            except (json.JSONDecodeError, TypeError):
                return (0, 0)
            required = metadata.get("required_reviews", [])
            if not required:
                return (0, 0)
            cursor.execute(
                "SELECT review_type FROM task_reviews WHERE task_id = ?",
                (task_id,),
            )
            present = {r[0] for r in cursor.fetchall()}
            return (len(required), len(set(required) & present))
    except sqlite3.Error as e:
        logger.debug("Database error querying reviews for task %d: %s", task_id, e)
        return (0, 0)


def get_commits_ahead_of_main(worktree_path: str | None) -> int:
    """Count commits ahead of origin/master."""
    if worktree_path is None:
        return 0
    try:
        result = subprocess.run(
            ["git", "-C", worktree_path, "log", "origin/master..HEAD", "--oneline"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return 0
    if result.returncode != 0:
        return 0
    return len([line for line in result.stdout.strip().split("\n") if line])


def get_finding_counts(task_id: int, db_path: str) -> dict[FindingPriority, int]:
    """Get P0/P1/P2/P3 finding counts from non-ignored reviews."""
    counts = {
        FindingPriority.P0: 0,
        FindingPriority.P1: 0,
        FindingPriority.P2: 0,
        FindingPriority.P3: 0,
    }
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT findings FROM task_reviews WHERE task_id = ? AND ignored = 0",
                (task_id,),
            )
            for (findings_json,) in cursor.fetchall():
                if not findings_json:
                    continue
                try:
                    findings = json.loads(findings_json)
                except (json.JSONDecodeError, TypeError):
                    continue
                for finding in findings:
                    p = finding.get("priority") or finding.get("severity", "")
                    if p in counts:
                        counts[p] += 1
    except sqlite3.Error as e:
        logger.debug("Database error querying findings for task %d: %s", task_id, e)
    return counts
