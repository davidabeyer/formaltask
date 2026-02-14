"""Epic validation and analysis logic.

Provides:
1. Blocking validation (circular deps, dangling deps)
2. Analysis (critical path, parallelism waves, file hotspots)
3. Advisory warnings (undersized tasks)
4. Orphan goal ref detection for implements field

Moved from formaltask.cli.commands.epic_finalize for reuse.
"""

import json
import logging

from formaltask.db.helpers import parse_depends_on
from formaltask.types import CriticalPathResult, FileHotspot

logger = logging.getLogger(__name__)


def get_ready_tasks(db_path: str, epic_name: str) -> list[dict]:
    """Get tasks that have no blockers and can be started immediately."""
    from formaltask.db.connection import DatabaseConnection

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, depends_on, status FROM tasks WHERE epic_name = ? ORDER BY id",
            (epic_name,),
        )
        all_tasks = cursor.fetchall()

    task_statuses = {t[0]: t[3] for t in all_tasks}
    ready_tasks = []

    for task_id, title, depends_on_json, status in all_tasks:
        if status != "open":
            continue

        depends_on = parse_depends_on(depends_on_json)

        all_deps_done = all(
            task_statuses.get(dep_id) in ("completed", "cancelled") for dep_id in depends_on
        )

        if not depends_on or all_deps_done:
            ready_tasks.append({"id": task_id, "title": title, "depends_on": depends_on})

    return ready_tasks


def find_dangling_dependencies(db_path: str, epic_name: str) -> list[tuple[int, int]]:
    """Find tasks with dependencies on non-existent task IDs.

    Args:
        db_path: Path to database
        epic_name: Name of epic to check

    Returns:
        List of (task_id, missing_dep_id) tuples
    """
    from formaltask.db.connection import DatabaseConnection

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        # Get all task IDs in the database (not just this epic)
        cursor.execute("SELECT id FROM tasks")
        all_task_ids = {row[0] for row in cursor.fetchall()}

        # Get tasks in this epic with their dependencies
        cursor.execute("SELECT id, depends_on FROM tasks WHERE epic_name = ?", (epic_name,))
        task_rows = cursor.fetchall()

    dangling = []
    for task_id, depends_on_json in task_rows:
        depends_on = parse_depends_on(depends_on_json)
        if not depends_on:
            continue

        for dep_id in depends_on:
            if dep_id not in all_task_ids:
                dangling.append((task_id, dep_id))

    return dangling


def calculate_critical_path(tasks: list[dict]) -> CriticalPathResult:
    """Calculate the longest dependency chain (critical path).

    Algorithm:
        Uses memoized Depth-First Search (DFS) with cycle detection to find
        the longest path through the task dependency graph.

    Args:
        tasks: List of task dicts with 'id' and 'depends_on' keys

    Returns:
        Dict with 'length' and 'path' (list of task IDs in order).
    """
    if not tasks:
        return {"length": 0, "path": []}

    task_ids = {t["id"] for t in tasks}
    deps_map = {t["id"]: t.get("depends_on", []) for t in tasks}

    CYCLE_SENTINEL = -1
    depths: dict[int, int] = {}
    paths: dict[int, list[int]] = {}
    visiting: set[int] = set()

    def get_depth(task_id: int) -> int:
        if task_id in depths:
            return depths[task_id]

        if task_id in visiting:
            depths[task_id] = CYCLE_SENTINEL
            paths[task_id] = []
            return CYCLE_SENTINEL

        visiting.add(task_id)

        deps = deps_map.get(task_id, [])
        valid_deps = [d for d in deps if d in task_ids]

        if not valid_deps:
            depths[task_id] = 1
            paths[task_id] = [task_id]
        else:
            max_dep_depth = 0
            best_path: list[int] = []
            for dep_id in valid_deps:
                dep_depth = get_depth(dep_id)
                if dep_depth == CYCLE_SENTINEL:
                    continue
                if dep_depth > max_dep_depth:
                    max_dep_depth = dep_depth
                    best_path = paths.get(dep_id, [])

            if max_dep_depth == 0 and valid_deps:
                all_cycle = all(depths.get(d) == CYCLE_SENTINEL for d in valid_deps)
                if all_cycle:
                    depths[task_id] = CYCLE_SENTINEL
                    paths[task_id] = []
                else:
                    depths[task_id] = 1
                    paths[task_id] = [task_id]
            else:
                depths[task_id] = max_dep_depth + 1
                paths[task_id] = best_path + [task_id]

        visiting.discard(task_id)
        return depths[task_id]

    for task in tasks:
        get_depth(task["id"])

    valid_depths = {tid: d for tid, d in depths.items() if d != CYCLE_SENTINEL}
    if not valid_depths:
        return {"length": 0, "path": []}

    max_task = max(valid_depths.keys(), key=lambda t: valid_depths[t])
    return {"length": valid_depths[max_task], "path": paths[max_task]}


def calculate_parallelism_waves(tasks: list[dict]) -> list[list[int]]:
    """Group tasks into waves based on when they can start.

    Wave 1: Tasks with no dependencies
    Wave 2: Tasks whose deps are all in Wave 1
    Wave N: Tasks whose deps are all in Waves 1..N-1

    Args:
        tasks: List of task dicts with 'id' and 'depends_on' keys

    Returns:
        List of waves, each wave is a list of task IDs
    """
    if not tasks:
        return []

    task_ids = {t["id"] for t in tasks}
    deps_map = {t["id"]: set(t.get("depends_on", [])) for t in tasks}
    remaining = set(task_ids)
    completed_in_waves: set[int] = set()
    waves: list[list[int]] = []

    while remaining:
        wave = []
        for task_id in remaining:
            deps = deps_map[task_id]
            valid_deps = deps & task_ids
            if valid_deps <= completed_in_waves:
                wave.append(task_id)

        if not wave:
            logger.warning(
                "Parallelism wave calculation stopped with %d tasks unreachable: %s",
                len(remaining),
                sorted(remaining),
            )
            break

        wave.sort()
        waves.append(wave)
        completed_in_waves.update(wave)
        remaining -= set(wave)

    return waves


def calculate_file_hotspots(tasks_with_spec: list[dict]) -> list[FileHotspot]:
    """Find files touched by multiple tasks.

    Args:
        tasks_with_spec: List of dicts with 'id' and 'spec_content' keys

    Returns:
        List of dicts with 'file' and 'task_ids' keys
    """
    from formaltask.validators.file_conflict import extract_files_from_spec

    file_to_tasks: dict[str, list[int]] = {}

    for task in tasks_with_spec:
        task_id = task.get("id")
        spec_content = task.get("spec_content", "")

        if task_id is None or not spec_content:
            continue

        files = extract_files_from_spec(spec_content)
        for file_path in files:
            if file_path not in file_to_tasks:
                file_to_tasks[file_path] = []
            file_to_tasks[file_path].append(task_id)

    return [
        {"file": file_path, "task_ids": task_ids}
        for file_path, task_ids in sorted(file_to_tasks.items())
        if len(task_ids) >= 2
    ]


def epic_finalize(epic_name: str, db_path: str) -> dict:
    """Run quality validation and analysis on an epic.

    Returns analysis dashboard data including:
    - Blocking validation errors (circular deps, dangling deps)
    - Critical path analysis
    - Parallelism waves
    - File hotspots
    - Quality warnings
    """
    from formaltask.db.connection import DatabaseConnection
    from formaltask.epics.yaml_parser import validate_task_quality
    from formaltask.tasks.dependencies import has_circular_dependencies
    from formaltask.validators.file_conflict import (
        detect_file_conflicts,
        detect_file_overlaps_without_dependency,
    )

    validation_errors: list[str] = []

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, description, metadata, depends_on FROM tasks WHERE epic_name = ? ORDER BY id",
            (epic_name,),
        )
        task_rows = cursor.fetchall()

        task_ids = [row[0] for row in task_rows]
        criteria_by_task: dict[int, list[str]] = {tid: [] for tid in task_ids}
        if task_ids:
            placeholders = ",".join("?" * len(task_ids))
            cursor.execute(  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
                f"SELECT task_id, text FROM acceptance_criteria WHERE task_id IN ({placeholders})",  # noqa: S608
                task_ids,
            )
            for task_id, text in cursor.fetchall():
                criteria_by_task[task_id].append(text)

    tasks = []
    tasks_with_deps = []
    tasks_for_conflict_check = []

    for task_id, title, description, metadata, depends_on_json in task_rows:
        criteria = criteria_by_task.get(task_id, [])
        depends_on = parse_depends_on(depends_on_json)

        tasks.append(
            {
                "title": title,
                "description": description or "",
                "criteria": criteria,
            }
        )

        tasks_with_deps.append(
            {
                "id": task_id,
                "title": title,
                "depends_on": depends_on,
            }
        )

        # Extract spec content from metadata for conflict detection
        spec_content = ""
        if metadata:
            try:
                meta = json.loads(metadata)
                spec_content = meta.get("artifact_content", "")
            except json.JSONDecodeError:
                pass
        tasks_for_conflict_check.append(
            {
                "id": task_id,
                "spec_content": spec_content,
                "depends_on": depends_on,
            }
        )

    # === BLOCKING VALIDATION ===
    has_circular_deps = has_circular_dependencies(db_path, epic_name)
    if has_circular_deps:
        validation_errors.append("Circular dependencies detected")

    dangling_deps = find_dangling_dependencies(db_path, epic_name)
    for task_id, missing_dep in dangling_deps:
        validation_errors.append(f"Task #{task_id} depends on #{missing_dep} which does not exist")

    # 3. Check for missing specs (Task #2242)
    # Reuse tasks_for_conflict_check which already parsed metadata for spec_content
    for task in tasks_for_conflict_check:
        if not task["spec_content"]:
            validation_errors.append(f"Task #{task['id']} missing spec")

    # === QUALITY VALIDATION (warnings) ===
    quality_result = validate_task_quality(tasks)

    # === ANALYSIS ===
    critical_path = calculate_critical_path(tasks_with_deps)
    parallelism_waves = calculate_parallelism_waves(tasks_with_deps)
    file_hotspots = calculate_file_hotspots(tasks_for_conflict_check)
    file_conflicts = detect_file_conflicts(tasks_for_conflict_check)
    risky_overlaps = detect_file_overlaps_without_dependency(tasks_for_conflict_check)
    ready_tasks = get_ready_tasks(db_path, epic_name)

    ready_for_sync = not validation_errors and not quality_result.errors

    return {
        "epic_name": epic_name,
        "ready_for_sync": ready_for_sync,
        "validation_errors": validation_errors,
        "quality_warnings": quality_result.warnings,
        "quality_errors": quality_result.errors,
        "has_circular_deps": has_circular_deps,
        "tasks_validated": len(tasks),
        "critical_path": critical_path,
        "parallelism_waves": parallelism_waves,
        "file_hotspots": file_hotspots,
        "file_conflicts": file_conflicts,
        "risky_overlaps": risky_overlaps,
        "ready_tasks": ready_tasks,
    }
