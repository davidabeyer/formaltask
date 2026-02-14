"""CompletionConfig dataclass - single source of truth for completion configuration.

Task #2821: Config computed ONCE, passed as DATA. All consumers receive this
dataclass instead of computing config themselves.

Design Principle: "If a function doesn't DECIDE, it shouldn't COMPUTE.
Pass values, not responsibilities."
"""

import json
from dataclasses import dataclass
from pathlib import Path

from formaltask.core import rules_config as rules
from formaltask.db.connection import DatabaseConnection
from formaltask.exceptions import TaskNotFoundError


@dataclass(frozen=True)
class CompletionConfig:
    """Frozen configuration for task completion checks.

    All fields are computed once by get_effective_config() and passed
    to consumers. No consumer should compute these values.
    """

    required_reviews: list[str]
    check_freshness: bool
    require_pr: bool
    require_pr_merged: bool
    documentation_required: bool
    check_docs: bool
    check_learnings: bool
    check_ac: bool


def get_effective_config(task_id: int, db_path: str | Path) -> CompletionConfig:
    """Load task metadata and merge with global defaults to create config.

    This is the SINGLE SOURCE OF TRUTH for completion configuration.
    All consumers call this once and use the returned config.

    Args:
        task_id: Task ID to load metadata for.
        db_path: Path to the FormalTask database.

    Returns:
        CompletionConfig with effective values (task overrides merged with defaults).

    Raises:
        TaskNotFoundError: If task doesn't exist.
    """
    db_path = Path(db_path) if isinstance(db_path, str) else db_path

    with DatabaseConnection(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT metadata FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

    if not row:
        raise TaskNotFoundError(task_id)

    metadata = _parse_metadata(row[0])

    # Merge task-specific overrides with global defaults
    return CompletionConfig(
        required_reviews=metadata.get("required_reviews") or list(rules.REQUIRED_REVIEWS),
        check_freshness=rules.CHECK_FRESHNESS,
        require_pr=metadata.get("require_pr", rules.REQUIRE_PR),
        require_pr_merged=metadata.get("require_pr_merged", rules.REQUIRE_PR_MERGED),
        documentation_required=metadata.get("documentation_required", False),
        check_docs=rules.CHECK_DOCS,
        check_learnings=rules.CHECK_LEARNINGS,
        check_ac=rules.CHECK_AC,
    )


def _parse_metadata(metadata_json: str | None) -> dict:
    """Parse metadata JSON, return empty dict on error."""
    if not metadata_json:
        return {}
    try:
        return json.loads(metadata_json)
    except json.JSONDecodeError:
        return {}
