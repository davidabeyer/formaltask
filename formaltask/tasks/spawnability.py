"""Spawnability functions - Task spawnability logic.

Extracted from EpicRepository (Task #1937) to determine which tasks can be spawned.
File conflict prevention added (Task #2275) to block tasks with file overlap.
Git diff file detection added (Task #2586) to reduce false positives.
Converted from class to functions (Task #2725).
"""

import json
import logging
import subprocess

from formaltask.paths import task_worktree
from formaltask.validators.file_conflict import extract_files_from_spec

logger = logging.getLogger(__name__)


def _extract_spec_content(metadata_json: str | None) -> str | None:
    """Extract spec content from task metadata JSON."""
    if not metadata_json:
        return None
    try:
        metadata = json.loads(metadata_json)
        return metadata.get("artifact_content") if metadata.get("artifact_type") == "spec" else None
    except (json.JSONDecodeError, TypeError):
        return None


def _get_worktree_modified_files(task_id: int, cursor) -> set[str] | None:
    """Get actual files modified in worktree via git diff.

    Task #2586: Use git diff instead of PRP text scanning for tasks with
    worktrees. This reduces false positives from PRP text mentioning files
    that aren't actually modified.

    Args:
        task_id: Task ID to check for worktree.
        cursor: Database cursor for epic lookup.

    Returns:
        - set[str]: File paths from git diff. Empty set means worktree exists
          but has no changes (task should NOT block other tasks).
        - None: No worktree or git diff failed. Caller should fall back to
          PRP text parsing for file detection.
    """
    worktree_path = task_worktree(task_id)
    if not worktree_path.exists():
        return None

    # Get the epic's feature_branch to use as diff base
    cursor.execute(
        """
        SELECT e.feature_branch FROM tasks t
        JOIN epics e ON t.epic_name = e.name WHERE t.id = ?
        """,
        (task_id,),
    )
    row = cursor.fetchone()
    base = row[0] if row and row[0] else "origin/master"

    # Normalize base branch - add origin/ prefix if needed
    if not base.startswith("origin/"):
        base = f"origin/{base}"

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base],
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            logger.debug(
                "git diff failed for task %d (exit %d): %s",
                task_id,
                result.returncode,
                result.stderr,
            )
            return None
        return {f.strip() for f in result.stdout.strip().split("\n") if f.strip()}
    except subprocess.TimeoutExpired:
        logger.warning("git diff timed out for task %d", task_id)
        return None
    except (FileNotFoundError, OSError) as e:
        logger.debug("git diff error for task %d: %s", task_id, e)
        return None


def _get_in_progress_files(cursor) -> set[str]:
    """Get all files touched by in-progress tasks.

    Task #2586: Prefer git diff for tasks with worktrees, fall back to
    PRP parsing when worktree doesn't exist or git diff fails.
    """
    from formaltask.utils.constants import TaskStatus

    cursor.execute(
        "SELECT id, metadata FROM tasks WHERE status = ?",
        (TaskStatus.IN_PROGRESS,),
    )

    files: set[str] = set()
    for task_id, metadata_json in cursor.fetchall():
        # Try git diff first for tasks with worktrees
        worktree_files = _get_worktree_modified_files(task_id, cursor)
        if worktree_files is not None:
            # Git diff succeeded (may be empty set for zero changes)
            files.update(worktree_files)
        else:
            # Fall back to PRP parsing when no worktree or git diff fails
            spec = _extract_spec_content(metadata_json)
            if spec:
                files.update(extract_files_from_spec(spec))
    return files


def _has_file_conflict(task_id: int, in_progress_files: set[str], cursor) -> bool:
    """Check if task touches any files already being modified.

    Task #2752: Extracted from inline logic for view-based refactoring.

    Args:
        task_id: Task ID to check for file conflicts.
        in_progress_files: Set of file paths currently being modified.
        cursor: Database cursor for task metadata lookup.

    Returns:
        True if task has file overlap with in-progress tasks, False otherwise.
    """
    cursor.execute("SELECT metadata FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if not row or not row[0]:
        return False
    spec = _extract_spec_content(row[0])
    if not spec:
        return False
    task_files = extract_files_from_spec(spec)
    return bool(task_files & in_progress_files)


def get_spawnable_tasks(db_path: str) -> list[int]:
    """Get all tasks ready to spawn across all non-archived epics.

    Uses task_ready_status view (Task #2752) for dependency + status checks.

    A task is spawnable if:
    1. Epic is not archived (archived_at IS NULL) - checked by view
    2. Status is 'open' - checked by view
    3. All dependencies are completed/cancelled - checked by view
    4. No file overlap with in-progress tasks (stays in Python - needs git subprocess)

    Complexity: O(n) where n is number of open tasks.

    Args:
        db_path: Path to the database file.

    Returns:
        List of task IDs that are ready to spawn, ordered by ID ascending.
    """
    import sqlite3

    from formaltask.db.connection import DatabaseConnection

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()

        try:
            # Query view for ready tasks (handles dependency + status + epic archived checks)
            cursor.execute("SELECT task_id FROM task_ready_status ORDER BY task_id")
            ready = [row[0] for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
            # View query fails if any task has malformed JSON in depends_on.
            # Fall back to Python-based logic that handles invalid JSON gracefully.
            if "malformed JSON" in str(e) or "JSON" in str(e):
                logger.warning("Malformed depends_on JSON in database, using fallback logic")
                ready = _get_ready_tasks_fallback(cursor)
            else:
                raise

        # File conflict filter (stays in Python - needs git subprocess)
        in_progress_files = _get_in_progress_files(cursor)
        if not in_progress_files:
            return ready

        return [t for t in ready if not _has_file_conflict(t, in_progress_files, cursor)]


def _get_ready_tasks_fallback(cursor) -> list[int]:
    """Fallback logic for get_spawnable_tasks when view query fails.

    Uses Python-based dependency checking with parse_depends_on which
    handles malformed JSON gracefully.
    """
    from formaltask.db.helpers import parse_depends_on
    from formaltask.utils.constants import TaskStatus

    # Get completed/cancelled task IDs
    cursor.execute(
        "SELECT id FROM tasks WHERE status IN (?, ?)",
        (TaskStatus.COMPLETED, TaskStatus.CANCELLED),
    )
    satisfied_ids = {row[0] for row in cursor.fetchall()}

    # Get all open tasks from non-archived epics
    cursor.execute(
        """SELECT t.id, t.depends_on FROM tasks t
           JOIN epics e ON t.epic_name = e.name
           WHERE e.archived_at IS NULL AND t.status = ?
           ORDER BY t.id""",
        (TaskStatus.OPEN,),
    )

    ready = []
    for task_id, depends_on_json in cursor.fetchall():
        depends_on = parse_depends_on(depends_on_json)
        if not depends_on or all(dep_id in satisfied_ids for dep_id in depends_on):
            ready.append(task_id)

    return ready


def get_spawnable_tasks_with_titles(db_path: str) -> list[dict]:
    """Get spawnable tasks with metadata for dashboard display.

    Args:
        db_path: Path to the database file.

    Returns:
        List of dicts with task metadata, ordered by ID ascending.
        Fields: id, title, description, epic_name, status, acceptance_criteria.
    """
    import json

    from formaltask.db.connection import DatabaseConnection

    task_ids = get_spawnable_tasks(db_path)
    if not task_ids:
        return []

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        placeholders = ",".join("?" * len(task_ids))
        cursor.execute(
            f"SELECT id, title, description, epic_name, status, acceptance_criteria_json "
            f"FROM tasks WHERE id IN ({placeholders}) ORDER BY id",  # noqa: S608
            task_ids,
        )
        results = []
        for row in cursor.fetchall():
            ac_json = row[5]
            ac_list = json.loads(ac_json) if ac_json else []
            results.append(
                {
                    "id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "epic_name": row[3],
                    "status": row[4],
                    "acceptance_criteria": ac_list,
                }
            )
        return results
