"""YAML parser for spec files.

Exports:
- SpecFormatError: Exception for invalid spec format
- EpicFormatError: Alias for backward compatibility (deprecated)
- parse_specs_dir: Parse spec directory to list of task dicts
- validate_task_quality: Quality checks on tasks
- ValidationIssue: Dataclass for validation issues
- ValidationResult: Dataclass for validation results
"""

import logging
import re
from dataclasses import dataclass, field

import yaml
from pydantic import ValidationError

from formaltask.epics.models import CriterionV2, SpecSpec

logger = logging.getLogger(__name__)


# =============================================================================
# Types
# =============================================================================


@dataclass
class ValidationIssue:
    """Single validation issue with context."""

    task_index: int
    field: str
    message: str
    severity: str = "warning"


@dataclass
class ValidationResult:
    """Result of task quality validation."""

    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        """Check if validation passed (no blocking errors)."""
        return not self.errors


class SpecFormatError(Exception):
    """Raised when spec file format is invalid."""


# =============================================================================
# Constants
# =============================================================================

# Undersized task thresholds (worktree spawn overhead ~5 min makes small tasks inefficient)
UNDERSIZED_MAX_FILES = 1
UNDERSIZED_MAX_CRITERIA = 2
UNDERSIZED_MAX_WORDS = 50
FILE_REF_PATTERN = r"[\w\-/]+\.\w+:\d+"

# Pattern to extract task references: $task[N].outputs.key -> (N, key)
TASK_REF_PATTERN = re.compile(r"\$task\[(\d+)\]\.outputs\.(\w+)")


# =============================================================================
# DB Row Conversion
# =============================================================================


def _criteria_to_db_rows(items: list[str | CriterionV2]) -> list[dict]:
    """Convert acceptance criteria to DB row format.

    Converts both plain strings and CriterionV2 objects to a uniform dict format
    suitable for database storage.

    Args:
        items: List of strings or CriterionV2 objects

    Returns:
        List of dicts with 'text' and 'command' keys:
        - CriterionV2: {'text': c.current, 'command': c.command}
        - str: {'text': s, 'command': ''}
    """
    result = []
    for item in items:
        if isinstance(item, CriterionV2):
            result.append({"text": item.current, "command": item.command})
        else:
            result.append({"text": item, "command": ""})
    return result


# =============================================================================
# Public API
# =============================================================================


def validate_task_quality(tasks: list[dict]) -> ValidationResult:
    """Validate task quality for epic decomposition.

    Performs undersized task detection only. Other quality checks
    are handled by Phase 2 agent-driven semantic analysis.
    """
    result = ValidationResult()

    for i, task in enumerate(tasks, 1):
        description = task.get("description", "")
        criteria = task.get("criteria", [])

        # Undersized task detection: single file, ≤2 criteria, <50 words
        file_refs = re.findall(FILE_REF_PATTERN, description)
        word_count = len(description.split())

        if (
            len(file_refs) <= UNDERSIZED_MAX_FILES
            and len(criteria) <= UNDERSIZED_MAX_CRITERIA
            and word_count < UNDERSIZED_MAX_WORDS
        ):
            result.warnings.append(
                ValidationIssue(
                    task_index=i,
                    field="size",
                    message=f"UNDERSIZED ({len(file_refs)} file(s), {len(criteria)} criteria, {word_count} words) - bundle with related task",
                )
            )

    return result


def parse_specs_dir(spec_dir: str) -> list[dict]:
    """Parse spec files from a directory.

    Reads spec files matching the pattern `task-{N}-*-spec.yaml` or `task-{N}-*.yaml`,
    sorts them numerically by the N prefix, validates each with SpecSpec model,
    and returns a list of task dictionaries.

    Args:
        spec_dir: Path to directory containing spec files

    Returns:
        List of task dictionaries with keys:
        - title: Task title
        - description: Task summary
        - criteria: Acceptance criteria in DB row format
        - depends_on: 0-indexed dependency positions
        - required_reviews: Review types list
        - skills: Skills list
        - spec_content: Original spec file content (full YAML)
        - documentation_required: Documentation required flag

    Raises:
        SpecFormatError: If directory doesn't exist, no spec files found,
            or any spec file fails validation
    """
    from pathlib import Path

    spec_path = Path(spec_dir)
    if not spec_path.is_dir():
        raise SpecFormatError(f"Spec directory not found: {spec_dir}")

    # Find spec files matching task-{N}-* pattern
    spec_files = list(spec_path.glob("task-*-*.yaml"))
    if not spec_files:
        raise SpecFormatError(f"No spec files found in {spec_dir}")

    # Extract task number from filename for sorting
    def get_task_number(path: Path) -> int:
        """Extract numeric task number from task-{N}-*.yaml filename."""
        name = path.stem  # e.g., "task-1-core-parser-spec"
        parts = name.split("-")
        if len(parts) >= 2 and parts[0] == "task":
            try:
                return int(parts[1])
            except ValueError:
                pass
        # Fallback: sort at end if pattern doesn't match
        return 999999

    # Sort files by task number (numeric, not lexicographic)
    spec_files = sorted(spec_files, key=get_task_number)

    tasks = []
    total_tasks = len(spec_files)

    for task_position, spec_file in enumerate(spec_files):
        spec_content = spec_file.read_text()

        try:
            data = yaml.safe_load(spec_content)
        except yaml.YAMLError as e:
            raise SpecFormatError(f"YAML syntax error in {spec_file.name}: {e}") from e

        if data is None:
            raise SpecFormatError(f"Empty YAML content in {spec_file.name}")

        try:
            spec = SpecSpec(**data)
        except ValidationError as e:
            raise SpecFormatError(f"Spec validation failed in {spec_file.name}: {e}") from e

        # Validate dependencies inline
        depends_on_0indexed = []
        if spec.depends_on:
            for dep in spec.depends_on:
                # Convert 1-indexed to 0-indexed
                dep_0idx = dep - 1

                # Self-dependency check
                if dep_0idx == task_position:
                    task_num = task_position + 1
                    raise SpecFormatError(
                        f"Task {task_num} ({spec_file.name}) cannot depend on itself"
                    )

                # Range check
                if dep < 1 or dep > total_tasks:
                    raise SpecFormatError(
                        f"Task {task_position + 1} ({spec_file.name}) has out-of-bounds "
                        f"dependency {dep} (only {total_tasks} tasks exist)"
                    )

                # Forward reference check
                if dep_0idx >= task_position:
                    raise SpecFormatError(
                        f"Task {task_position + 1} ({spec_file.name}) has forward dependency "
                        f"on task {dep}"
                    )

                # Duplicate check
                if dep_0idx in depends_on_0indexed:
                    raise SpecFormatError(
                        f"Task {task_position + 1} ({spec_file.name}) has duplicate "
                        f"dependency {dep}"
                    )

                depends_on_0indexed.append(dep_0idx)

        # Auto-infer dependencies from $task[N].outputs references in inputs
        if spec.inputs:
            for input_value in spec.inputs.values():
                for match in TASK_REF_PATTERN.finditer(input_value):
                    ref_task_num = int(match.group(1))
                    ref_task_0idx = ref_task_num - 1

                    # Range check (1-indexed, must be valid task number)
                    if ref_task_num < 1 or ref_task_num > total_tasks:
                        raise SpecFormatError(
                            f"Task {task_position + 1} ({spec_file.name}) has out-of-bounds "
                            f"input reference $task[{ref_task_num}] (only {total_tasks} tasks exist)"
                        )

                    # Forward reference check (same validation as explicit deps)
                    if ref_task_0idx >= task_position:
                        raise SpecFormatError(
                            f"Task {task_position + 1} ({spec_file.name}) has forward dependency "
                            f"on task {ref_task_num} via input reference"
                        )

                    # Add if not already in deps (avoid duplicates)
                    if ref_task_0idx not in depends_on_0indexed:
                        depends_on_0indexed.append(ref_task_0idx)

        tasks.append(
            {
                "title": spec.title,
                "description": spec.summary,
                "criteria": _criteria_to_db_rows(spec.acceptance_criteria),
                "depends_on": depends_on_0indexed,
                "required_reviews": spec.required_reviews or [],
                "skills": spec.skills or [],
                "spec_content": spec_content,
                "documentation_required": None,  # Not in SpecSpec currently
                "inputs": spec.inputs,
                "outputs": spec.outputs,
                "prompt_template": spec.prompt_template,
            }
        )

    return tasks
