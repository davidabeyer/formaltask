"""Feature branch target checker for pre-push hook.

Blocks task branches from being pushed to master when their epic has a feature_branch set.
"""

import re
import sqlite3

from formaltask.db.connection import DatabaseConnection


def check_feature_branch_target(branch: str, target_ref: str, db_path: str) -> dict:
    """Check if a task branch should be blocked from pushing to a target.

    Args:
        branch: Current branch name (e.g., 'task-100')
        target_ref: Target ref being pushed to (e.g., 'refs/heads/master')
        db_path: Path to the FormalTask database

    Returns:
        dict with keys:
            - allowed: bool - True if push is allowed
            - feature_branch: str|None - The epic's feature branch if set
            - reason: str - Explanation of the result
    """
    result = {"allowed": True, "feature_branch": None, "reason": ""}

    # Only check task branches
    match = re.match(r"^task-(\d+)", branch)
    if not match:
        result["reason"] = "Not a task branch"
        return result

    task_id = int(match.group(1))

    # Only check pushes to master/main
    if target_ref not in ("refs/heads/master", "refs/heads/main"):
        result["reason"] = "Not pushing to master/main"
        return result

    # Query epic's feature_branch for this task
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT e.feature_branch FROM tasks t
                JOIN epics e ON t.epic_name = e.name
                WHERE t.id = ?
                """,
                (task_id,),
            )
            row = cursor.fetchone()

            if row is None:
                result["reason"] = f"Task #{task_id} not found in database"
                return result

            feature_branch = row[0]
            if feature_branch:
                result["allowed"] = False
                result["feature_branch"] = feature_branch
                result["reason"] = f"Epic has feature branch: {feature_branch}"
            else:
                result["reason"] = "Epic has no feature branch"

    except sqlite3.Error as e:
        result["reason"] = f"Database error: {e}"

    return result
