"""TaskGuards - Workflow enforcement for FormalTask v5."""

import json
import logging
import sqlite3

from formaltask.db.connection import DatabaseConnection
from formaltask.db.helpers import ensure_task_exists, parse_depends_on
from formaltask.utils.constants import TaskStatus

logger = logging.getLogger(__name__)

# Maximum warnings to display before truncating (for warn_if_dependency_code_missing)
MAX_DEPENDENCY_WARNINGS = 5


class GuardViolation(Exception):
    """Exception raised when a guard detects a workflow violation."""

    def __init__(self, message: str, suggested_action: str):
        """Initialize guard violation with message and suggested action.

        Args:
            message: Description of the violation
            suggested_action: Command or action to fix the issue
        """
        self.message = message
        self.suggested_action = suggested_action
        super().__init__(f"{message}\nSuggested action: {suggested_action}")


class TaskGuards:
    """Workflow enforcement guards for FormalTask v5."""

    def __init__(self, db_path: str):
        """Initialize guards with database access.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path

    def check_evidence_required(self, task_id: int) -> None:
        """Guard 2: Prevent completing task without evidence (commits or completion_evidence).

        Task must have at least 1 commit linked OR have completion_evidence set.
        completion_evidence is for tasks where work was already done before agent started.

        Args:
            task_id: Task ID to check
        """
        with DatabaseConnection(self.db_path) as conn:
            cursor = conn.cursor()

            # Check if task has any commits
            cursor.execute("SELECT COUNT(*) FROM commits WHERE task_id = ?", (task_id,))
            result = cursor.fetchone()
            commit_count = result[0] if result else 0

            if commit_count > 0:
                return  # Has commits, evidence requirement satisfied

            # Check for completion_evidence (Task #1893)
            # Gracefully handle missing column for pre-migration databases
            try:
                cursor.execute("SELECT completion_evidence FROM tasks WHERE id = ?", (task_id,))
                result = cursor.fetchone()
                completion_evidence = result[0] if result else None

                if completion_evidence:
                    return  # Has completion_evidence, evidence requirement satisfied
            except sqlite3.OperationalError:
                # Column doesn't exist yet - continue to require commits
                logger.debug("completion_evidence column not found, requiring commits")

            logger.warning(
                f"Guard 2 violation: Task #{task_id} blocked - no commits linked (evidence required)"
            )
            raise GuardViolation(
                f"Task #{task_id} has no commits - evidence required before completion",
                f"Link commits to task using: /commit-link {task_id}",
            )

    def check_dependencies_satisfied(self, task_id: int) -> None:
        """Guard: Prevent starting task when dependencies not completed.

        Uses task_blocked_status view (Task #2752) to check if task is blocked.
        A dependency is satisfied if its status is 'completed' OR 'cancelled'.

        Args:
            task_id: ID of task to check for dependency completion

        Raises:
            ValueError: If task with given ID is not found
            GuardViolation: If any dependency task is not yet completed/cancelled
        """
        with DatabaseConnection(self.db_path) as conn:
            cursor = conn.cursor()
            # Ensure task exists (raises ValueError if not)
            ensure_task_exists(cursor, task_id)

            # Query view - returns row only if task is blocked
            cursor.execute(
                "SELECT blocking_task_ids FROM task_blocked_status WHERE task_id = ?",
                (task_id,),
            )
            row = cursor.fetchone()

            if not row or not row[0]:
                return  # Not blocked

            blocking_ids = json.loads(row[0])
            if not blocking_ids:
                return  # Empty blocking list

            # Fetch titles for error message (Task #1826)
            placeholders = ",".join("?" * len(blocking_ids))
            cursor.execute(  # nosemgrep: sqlalchemy-execute-raw-query
                f"SELECT id, title FROM tasks WHERE id IN ({placeholders})",  # noqa: S608 - placeholders is "?,?,?" not user input
                blocking_ids,
            )
            titles = {row[0]: row[1] for row in cursor.fetchall()}

            # Format with titles: "#ID (Title)" or "#ID" if not found
            formatted = [
                f"#{dep_id} ({titles[dep_id]})" if dep_id in titles else f"#{dep_id}"
                for dep_id in blocking_ids
            ]
            formatted_str = ", ".join(formatted)
            logger.warning(
                f"Dependency guard violation: Task #{task_id} blocked - dependencies {blocking_ids} not completed"
            )
            raise GuardViolation(
                f"Task #{task_id} blocked - dependencies not completed: {formatted_str}",
                f"Complete dependencies first: {formatted_str}",
            )

    # Task #2186: _get_unverified_pr_statuses removed - github_pr_number column deleted

    def warn_if_dependency_code_missing(self, task_id: int) -> list[str]:
        """Advisory check - returns warnings, NEVER blocks.

        Returns:
            list[str]: Warning messages. Empty if no issues or on any error.
        """
        from formaltask.git import utils as git_utils

        try:
            warnings = []
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT depends_on FROM tasks WHERE id = ?", (task_id,))
                result = cursor.fetchone()
                if not result:
                    return []

                depends_on = parse_depends_on(result[0])
                if not depends_on:
                    return []

                placeholders = ",".join("?" * len(depends_on))
                # placeholders is safe: computed as ",".join("?" * len(depends_on))
                # Task #2186: github_pr_number removed from schema - PR info now from GitHub API
                cursor.execute(  # nosemgrep: sqlalchemy-execute-raw-query
                    f"SELECT id, title, head_commit_sha, status, metadata FROM tasks WHERE id IN ({placeholders})",  # noqa: S608 - placeholders is "?,?,?" not user input
                    depends_on,
                )
                deps = {
                    row[0]: {
                        "title": row[1],
                        "sha": row[2],
                        "status": row[3],
                        "metadata": row[4],
                    }
                    for row in cursor.fetchall()
                }

                # P3 FIX: Compute target branch once, outside loop
                # Check against epic's feature_branch if set, otherwise origin's default branch
                # (matches spawn_worker behavior from Task #2428)
                cursor.execute(
                    """SELECT e.feature_branch FROM tasks t
                       JOIN epics e ON t.epic_name = e.name
                       WHERE t.id = ?""",
                    (task_id,),
                )
                row = cursor.fetchone()
                feature_branch = row[0] if row and row[0] else None
                if feature_branch:
                    # Strip origin/ prefix if present, we add it back
                    branch_name = feature_branch.replace("origin/", "")
                    target_branch = f"origin/{branch_name}"
                else:
                    branch_name = git_utils.get_default_branch()
                    target_branch = f"origin/{branch_name}"

                # Auto-fetch to ensure origin ref is current (prevents stale ref issues)
                # Graceful: fetch failure doesn't block - just uses potentially stale ref
                git_utils.fetch_remote("origin", branch_name)

                for dep_id in depends_on:
                    dep = deps.get(dep_id)
                    if not dep:
                        continue

                    title = dep["title"] or f"Task #{dep_id}"

                    # Case 1: No SHA - skip (can't verify)
                    if not dep.get("sha"):
                        # If completed but no SHA/PR, trust it (legacy task)
                        if dep["status"] == TaskStatus.COMPLETED:
                            continue
                        # Non-completed without SHA - skip
                        continue

                    # Case 3: Git ancestry check
                    sha = dep["sha"]
                    is_anc = git_utils.is_ancestor(sha, target=target_branch)

                    if is_anc is True:
                        continue

                    if is_anc is None:
                        warnings.append(
                            f"Dependency #{dep_id} ({title}) commit {sha[:8]} not found - may have been force-pushed"
                        )
                    else:
                        # Search target branch for task ID (handles squash merges)
                        if git_utils.find_task_in_commits(dep_id, target=target_branch):
                            continue
                        # PR number fallback: extract from pr_url metadata
                        pr_number = None
                        if dep.get("metadata"):
                            try:
                                meta = json.loads(dep["metadata"])
                                pr_url = meta.get("pr_url", "")
                                if "/pull/" in pr_url:
                                    pr_number = int(pr_url.split("/pull/")[-1].split("/")[0])
                            except (json.JSONDecodeError, ValueError):
                                pass
                        if pr_number and git_utils.find_pr_in_commits(
                            pr_number, target=target_branch
                        ):
                            continue
                        warnings.append(
                            f"Dependency #{dep_id} ({title}) code may not be in branch - merge or rebase first"
                        )

            # Truncate if too many warnings
            if len(warnings) > MAX_DEPENDENCY_WARNINGS:
                remaining = len(warnings) - MAX_DEPENDENCY_WARNINGS
                warnings = warnings[:MAX_DEPENDENCY_WARNINGS]
                warnings.append(f"...and {remaining} more dependencies may not be in branch")

            return warnings
        except Exception as e:
            logger.debug("Advisory check failed for task %s: %s", task_id, e)
            return []
