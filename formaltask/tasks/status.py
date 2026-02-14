"""Task status checker for pre-merge hook.

Provides check_merge_allowed() to:
1. Extract task ID from branch name (pattern: task[-/][0-9]+)
2. Query task status from formaltask.db
3. Check if merge should be allowed based on task completion status

This module bypasses formaltask_sql_guard since it only performs
read-only SELECT queries.
"""

import json
import re
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

from formaltask.db.connection import DatabaseConnection


def check_merge_allowed(  # noqa: C901, PLR0912, PLR0915
    branch_name: str, db_path: str | Path | None = None
) -> dict[str, Any]:
    """Check if merge is allowed for the given branch.

    Args:
        branch_name: Git branch name to check
        db_path: Optional path to formaltask.db (auto-detected if not provided)

    Returns:
        Dict with:
            - allowed: bool - whether merge is permitted
            - task_id: int | None - extracted task ID
            - reason: str - explanation for the decision
    """
    # Extract task ID from branch name (pattern: task[-/][0-9]+)
    match = re.search(r"task[-/](\d+)", branch_name, re.IGNORECASE)
    task_id = int(match.group(1)) if match else None

    # Non-task branches are always allowed
    if task_id is None:
        return {
            "allowed": True,
            "task_id": None,
            "reason": "No task ID found in branch name - merge allowed",
        }

    # Resolve database path if not provided
    if db_path is None:
        from formaltask.db.path import get_db_path

        db_path = get_db_path()

    # Get task status from database
    db_path_obj = Path(db_path) if isinstance(db_path, str) else db_path
    try:
        if not db_path_obj.exists():
            raise FileNotFoundError(f"Database not found: {db_path_obj}")

        with DatabaseConnection(str(db_path_obj)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
        status = row[0] if row else None
    except (sqlite3.Error, FileNotFoundError) as e:
        # Database error - allow merge with warning (fail-open for developer experience)
        return {
            "allowed": True,
            "task_id": task_id,
            "reason": f"Database error: {e} - merge allowed with warning",
        }

    # Task not found - allow merge (may be old/deleted task)
    if status is None:
        return {
            "allowed": True,
            "task_id": task_id,
            "reason": f"Task {task_id} not found in database - merge allowed",
        }

    # Cancelled tasks can be merged without review
    if status == "cancelled":
        return {
            "allowed": True,
            "task_id": task_id,
            "reason": f"Task {task_id} is cancelled - merge allowed",
        }

    # Non-completed tasks must be completed first
    if status != "completed":
        return {
            "allowed": False,
            "task_id": task_id,
            "reason": f"Task {task_id} is {status} - must be completed before merge",
        }

    # Task is completed - now check Greptile review
    # Get PR number for branch using gh CLI
    pr_result = subprocess.run(
        ["gh", "pr", "list", "--head", branch_name, "--json", "number"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    pr_number = None
    if pr_result.returncode == 0:
        try:
            prs = json.loads(pr_result.stdout)
            if prs:
                pr_number = prs[0]["number"]
        except (json.JSONDecodeError, KeyError, IndexError):
            pass

    # No PR found - allow merge (direct merge or PR not created yet)
    if pr_number is None:
        return {
            "allowed": True,
            "task_id": task_id,
            "reason": f"Task {task_id} completed, no PR found - merge allowed",
        }

    # Fetch Greptile review comment from PR
    # Greptile comments contain "Confidence Score: X/5"
    greptile_result = subprocess.run(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "comments",
            "-q",
            '[.comments[] | select(.body | test("Confidence Score:"))] | last | {body: .body}',
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    greptile = None
    if greptile_result.returncode == 0:
        try:
            # jq returns null for empty results
            if greptile_result.stdout.strip() not in ("", "null"):
                greptile = json.loads(greptile_result.stdout)
        except json.JSONDecodeError:
            pass

    if greptile is None:
        return {
            "allowed": False,
            "task_id": task_id,
            "reason": f"Task {task_id} completed but PR #{pr_number} awaiting Greptile review",
        }

    # Parse Greptile findings from comment body
    body = greptile["body"]
    # Extract confidence score (pattern: "Confidence Score: X/5")
    score_match = re.search(r"Confidence Score:\s*(\d)/5", body)
    score = int(score_match.group(1)) if score_match else 0
    passed = score >= 3

    # Extract findings (lines starting with - and containing [BUG], [SEC], or [PERF])
    greptile_findings = []
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("-") and any(tag in line for tag in ("[BUG]", "[SEC]", "[PERF]")):
            greptile_findings.append(line)

    if not passed:
        # Build detailed error message with findings
        finding_lines = "\n".join(f"  {f}" for f in greptile_findings[:5])
        reason = f"Greptile score {score}/5 (need 3+) on PR #{pr_number}"
        if greptile_findings:
            reason += f"\n\nFindings:\n{finding_lines}"
        return {
            "allowed": False,
            "task_id": task_id,
            "reason": reason,
            "greptile_score": score,
            "greptile_findings": greptile_findings,
        }

    # Greptile passed
    return {
        "allowed": True,
        "task_id": task_id,
        "reason": f"Task {task_id} completed, Greptile score {score}/5 - merge allowed",
    }


def main() -> int:
    """CLI entry point for pre-merge-commit hook.

    Reads branch name from git, checks merge status, and exits
    with appropriate code.

    Returns:
        0 if merge allowed, 1 if blocked
    """
    import sys

    # Get current branch name
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        print("Error: Failed to get current branch name", file=sys.stderr)
        return 1

    branch_name = result.stdout.strip()
    check_result = check_merge_allowed(branch_name)

    if not check_result["allowed"]:
        print(f"MERGE BLOCKED: {check_result['reason']}", file=sys.stderr)
        print("", file=sys.stderr)

        # Check if this is a Greptile-related block
        if "greptile_score" in check_result or "awaiting Greptile" in check_result.get(
            "reason", ""
        ):
            print("Greptile review issues must be addressed before merge.", file=sys.stderr)
            print("", file=sys.stderr)
            print("Options:", file=sys.stderr)
            print("  1. Address the findings and push updated code", file=sys.stderr)
            print("  2. Wait for Greptile to re-review after push", file=sys.stderr)
        else:
            # Task completion issue
            print("To merge, complete the task first:", file=sys.stderr)
            print("", file=sys.stderr)
            print("  CLI (works in terminal/tmux):", file=sys.stderr)
            print(
                f"    python3 -m formaltask.cli.pm task-complete {check_result['task_id']}",
                file=sys.stderr,
            )
            print("", file=sys.stderr)
            print("  Claude Code session:", file=sys.stderr)
            print(f"    /task-complete {check_result['task_id']}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
