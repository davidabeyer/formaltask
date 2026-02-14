"""File conflict detection for specs.

Extract file mentions from spec text and detect conflicts (files touched by 2+ tasks).
"""

import os.path
import re

# Patterns: "modify X.py", "edit X.py", "create X.py", "update X.py", `path/file.ext`
FILE_PATTERNS = (
    re.compile(r"\bmodify\s+(\S+\.\w+)", re.IGNORECASE),
    re.compile(r"\bedit\s+(\S+\.\w+)", re.IGNORECASE),
    re.compile(r"\bcreate\s+(\S+\.\w+)", re.IGNORECASE),
    re.compile(r"\bupdate\s+(\S+\.\w+)", re.IGNORECASE),
    re.compile(r"`([^`]+\.\w+)`"),
)


def extract_files_from_spec(spec_content: str) -> set[str]:
    """Extract file mentions from spec content."""
    files = set()
    for pattern in FILE_PATTERNS:
        for match in pattern.finditer(spec_content):
            files.add(match.group(1))

    return {
        os.path.normpath(f.lstrip("`")) for f in files if not f.startswith(("http://", "https://"))
    }


def _build_file_to_tasks(tasks: list[dict]) -> tuple[dict[str, list[int]], dict[int, set[int]]]:
    """Build file→task_ids and task→deps mappings."""
    file_to_tasks: dict[str, list[int]] = {}
    deps_map: dict[int, set[int]] = {}

    for task in tasks:
        task_id = task.get("id")
        if task_id is None:
            continue

        deps_map[task_id] = set(task.get("depends_on") or [])

        if spec := task.get("spec_content"):
            for f in extract_files_from_spec(spec):
                file_to_tasks.setdefault(f, []).append(task_id)

    return file_to_tasks, deps_map


def detect_file_conflicts(
    tasks: list[dict], *, check_deps: bool = False
) -> list[tuple[str, list[int]]] | list[tuple[str, int, int]]:
    """Detect files touched by 2+ tasks.

    Args:
        tasks: List of task dicts with 'id', 'spec_content', and optionally 'depends_on'
        check_deps: If True, only return pairs where neither task depends on the other

    Returns:
        Without check_deps: List of (file_path, [task_ids]) for conflicts
        With check_deps: List of (file_path, task_a_id, task_b_id) for risky overlaps
    """
    file_to_tasks, deps_map = _build_file_to_tasks(tasks)

    if not check_deps:
        return [(f, ids) for f, ids in file_to_tasks.items() if len(ids) >= 2]

    # With deps check: find pairs without dependency relationship
    risky: list[tuple[str, int, int]] = []
    for f, ids in file_to_tasks.items():
        if len(ids) < 2:
            continue
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                if a not in deps_map.get(b, set()) and b not in deps_map.get(a, set()):
                    risky.append((f, a, b))
    return risky


def detect_file_overlaps_without_dependency(tasks: list[dict]) -> list[tuple[str, int, int]]:
    """Find file overlaps where tasks lack dependency relationship.

    Backward-compatible alias for detect_file_conflicts(tasks, check_deps=True).
    """
    return detect_file_conflicts(tasks, check_deps=True)  # type: ignore[return-value]
