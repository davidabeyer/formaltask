"""Dependency management for task graphs - standalone functions.

Extracts dependency logic from EpicRepository for isolation and testing.
Reuses existing circular_dependency_checker.py.
Refactored to antirez-style functions (Task #2627).
"""

import json
import logging
import sqlite3
from typing import NotRequired, TypedDict

from formaltask.db.connection import DatabaseConnection
from formaltask.db.helpers import ensure_task_exists, parse_depends_on, transaction
from formaltask.exceptions import TaskNotFoundError
from formaltask.utils.constants import TaskStatus


class DependentTask(TypedDict):
    """Dependent task info returned by get_dependent_tasks()."""

    id: int
    title: str
    epic_name: str
    status: NotRequired[str]


__all__: list[str] = [
    "find_dependency_cycle",
    "update_task_dependencies",
    "get_ready_tasks",
    "has_circular_dependencies",
    "get_dependency_graph",
    "get_dependent_tasks",
    "validate_epic_health",
]

logger = logging.getLogger(__name__)


def find_dependency_cycle(graph: dict[int, list[int]]) -> list[int] | None:
    """Find circular dependency in task graph using DFS.

    Args:
        graph: Dict mapping task_id to list of dependency task_ids

    Returns:
        List of task IDs forming cycle if found, None otherwise
    """
    state: dict[int, int] = dict.fromkeys(graph, 0)

    def dfs(node: int, path: list[int]) -> list[int] | None:
        if node not in state:
            return None
        if state[node] == 1:
            return path + [node]
        if state[node] == 2:
            return None
        state[node] = 1
        for dep in graph.get(node, []):
            if cycle := dfs(dep, path + [node]):
                return cycle
        state[node] = 2
        return None

    for task_id in graph:
        if state[task_id] == 0:
            if cycle := dfs(task_id, []):
                return cycle
    return None


def update_task_dependencies(db_path: str, task_id: int, depends_on_ids: list[int]) -> None:
    """Update dependencies for an existing task.

    Args:
        db_path: Path to SQLite database file
        task_id: ID of task to update
        depends_on_ids: List of task IDs this task depends on

    Raises:
        ValueError: If task not found, self-referential, or depends on non-existent task
    """
    # Validate: no self-reference
    if task_id in depends_on_ids:
        raise ValueError(f"Task #{task_id} cannot depend on itself (self-referential dependency)")

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()

        try:
            with transaction(conn):
                # Check task exists
                ensure_task_exists(cursor, task_id)

                # Validate: all dependency IDs exist
                for dep_id in depends_on_ids:
                    ensure_task_exists(cursor, dep_id)

                # Update depends_on
                depends_on_json = json.dumps(depends_on_ids)
                cursor.execute(
                    "UPDATE tasks SET depends_on = ? WHERE id = ?",
                    (depends_on_json, task_id),
                )

                # Check for circular dependencies before committing
                cursor.execute("SELECT epic_name FROM tasks WHERE id = ?", (task_id,))
                epic_row = cursor.fetchone()
                if epic_row:
                    epic_name = epic_row[0]
                    # Build graph with the new dependencies
                    cursor.execute(
                        "SELECT id, depends_on FROM tasks WHERE epic_name = ?",
                        (epic_name,),
                    )
                    graph: dict[int, list[int]] = {}
                    for graph_task_id, deps_json in cursor.fetchall():
                        graph[graph_task_id] = parse_depends_on(deps_json)

                    if find_dependency_cycle(graph) is not None:
                        raise ValueError(
                            f"Cannot update task #{task_id} dependencies: "
                            "would create circular dependency"
                        )
            logger.info("Updated task #%d dependencies to %s", task_id, depends_on_ids)
        except (sqlite3.Error, ValueError, TaskNotFoundError) as e:
            logger.error("Failed to update task #%d dependencies: %s", task_id, e)
            raise


def get_ready_tasks(db_path: str, epic_name: str) -> list[int]:
    """Get tasks ready to start (open status, all dependencies satisfied).

    Uses task_ready_status view (Task #2752) for dependency checking.

    A task is ready if:
    1. Status is 'open'
    2. Either has no dependencies (depends_on is NULL or '[]')
    3. Or all tasks in depends_on have status 'completed' OR 'cancelled'

    Args:
        db_path: Path to SQLite database file
        epic_name: Name of epic to query

    Returns:
        List of task IDs ready to start
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT task_id FROM task_ready_status WHERE epic_name = ? ORDER BY task_id",
            (epic_name,),
        )
        return [row[0] for row in cursor.fetchall()]


def has_circular_dependencies(db_path: str, epic_name: str) -> bool:
    """Check if epic has any circular dependencies.

    Uses find_dependency_cycle() for DFS-based cycle detection.

    Args:
        db_path: Path to SQLite database file
        epic_name: Name of epic to check

    Returns:
        True if circular dependencies exist, False otherwise
    """
    graph = get_dependency_graph(db_path, epic_name)
    return find_dependency_cycle(graph) is not None


def get_dependency_graph(db_path: str, epic_name: str) -> dict[int, list[int]]:
    """Get dependency graph for an epic.

    Args:
        db_path: Path to SQLite database file
        epic_name: Name of epic to query

    Returns:
        Dict mapping each task ID to list of task IDs it depends on
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, depends_on FROM tasks WHERE epic_name = ?",
            (epic_name,),
        )
        tasks = cursor.fetchall()

        graph: dict[int, list[int]] = {}
        for task_id, depends_on_json in tasks:
            graph[task_id] = parse_depends_on(depends_on_json)

        return graph


def get_dependent_tasks(db_path: str, task_id: int) -> list[DependentTask]:
    """Find all tasks that depend on the given task.

    Searches ALL tasks (cross-epic) since depends_on can reference
    any task ID regardless of epic. Uses full table scan which is
    acceptable for FormalTask scale (<1000 tasks).

    Args:
        db_path: Path to SQLite database file
        task_id: Task ID to find dependents for

    Returns:
        List of DependentTask dicts with keys: id, title, epic_name, status.
        Returns empty list if task_id doesn't exist or has no dependents.
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, epic_name, status, depends_on FROM tasks")
        dependents: list[DependentTask] = []
        for row_task_id, title, epic, status, deps_json in cursor.fetchall():
            deps = parse_depends_on(deps_json)
            if task_id in deps:
                dependents.append(
                    {"id": row_task_id, "title": title, "epic_name": epic, "status": status}
                )
        return dependents


def _check_dep_validity(
    dep_id: int,
    task_id: int,
    all_tasks: dict[int, tuple[str, str]],
    cancelled: set[int],
    epic_name: str,
) -> dict[str, int | str] | None:
    """Check if a dependency is valid, return issue dict if invalid.

    Args:
        dep_id: The dependency task ID to validate.
        task_id: The task that has this dependency.
        all_tasks: Mapping of task_id -> (status, epic_name) for all tasks.
        cancelled: Set of task IDs with cancelled status.
        epic_name: Epic name of the task being validated.

    Returns:
        Issue dict with keys (task_id, issue, orphan_dep) if invalid,
        None if the dependency is valid.
    """
    if dep_id not in all_tasks:
        return {
            "task_id": task_id,
            "issue": f"Depends on non-existent task #{dep_id}",
            "orphan_dep": dep_id,
        }
    if dep_id in cancelled:
        return {
            "task_id": task_id,
            "issue": f"Depends on cancelled task #{dep_id}",
            "orphan_dep": dep_id,
        }
    if all_tasks[dep_id][1] != epic_name:
        return {
            "task_id": task_id,
            "issue": f"Cross-epic dependency on task #{dep_id}",
            "orphan_dep": dep_id,
        }
    return None


def _collect_dep_issues(
    task_id: int,
    deps_json: str | None,
    all_tasks: dict[int, tuple[str, str]],
    cancelled: set[int],
    epic_name: str,
) -> list[dict[str, int | str]]:
    """Parse deps and collect validity issues for a single task.

    Args:
        task_id: Task ID to check dependencies for.
        deps_json: JSON string of dependency IDs, or None if no deps.
        all_tasks: Mapping of task_id -> (status, epic_name) for all tasks.
        cancelled: Set of task IDs with cancelled status.
        epic_name: Epic name of the task being validated.

    Returns:
        List of issue dicts, each with keys (task_id, issue, orphan_dep).
        Empty list if no issues or malformed JSON.
    """
    deps = parse_depends_on(deps_json)
    return [
        issue
        for dep_id in deps
        if (issue := _check_dep_validity(dep_id, task_id, all_tasks, cancelled, epic_name))
    ]


def validate_epic_health(db_path: str, epic_name: str) -> list[dict]:
    """Detect tasks with orphaned or invalid dependencies.

    Checks for:
    - Dependencies on cancelled tasks (error)
    - Dependencies on non-existent tasks (error)
    - Cross-epic dependencies (warning - valid but notable)

    Args:
        db_path: Path to SQLite database file
        epic_name: Name of epic to validate

    Returns:
        List of issues with keys: task_id, issue, orphan_dep.
        Returns empty list if epic doesn't exist or has no issues.
        Note: Cross-epic deps are warnings; parse issue text to distinguish.
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, depends_on FROM tasks WHERE epic_name = ?", (epic_name,))
        epic_tasks = cursor.fetchall()
        cursor.execute("SELECT id, status, epic_name FROM tasks")
        all_tasks = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
        cancelled = {
            task_id for task_id, (status, _) in all_tasks.items() if status == TaskStatus.CANCELLED
        }
        issues: list[dict] = []
        for task_id, deps_json in epic_tasks:
            issues.extend(_collect_dep_issues(task_id, deps_json, all_tasks, cancelled, epic_name))
        return issues
