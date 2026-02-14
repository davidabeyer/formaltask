"""Rules configuration constants (Task #2873).

Module-level constants for task completion logic, configurable via environment variables.
Extracted from legacy module for clean separation between constants and rules.

Environment variables:
- FORMALTASK_BLOCK_PRIORITIES: Comma-separated priorities that block completion (default: P0,P1)
- FORMALTASK_MAX_LOW_FINDINGS: Max non-blocking findings before blocking (default: unlimited)
- FORMALTASK_REQUIRE_PR: Whether PR is required for completion (default: false)
- FORMALTASK_REQUIRE_PR_MERGED: Whether PR must be merged (default: false)
- FORMALTASK_CHECK_FRESHNESS: Whether to check review freshness (default: true)
- FORMALTASK_CHECK_DOCS: Whether to check documentation_required (default: true)
- FORMALTASK_CHECK_LEARNINGS: Whether to require at least one learning captured (default: false)
- FORMALTASK_REQUIRED_REVIEWS: Comma-separated required review types (default: code-quality)
- FORMALTASK_CHECK_AC: Whether to check acceptance criteria commands (default: true)
"""

import os

from formaltask.utils.constants import FindingPriority


def _parse_bool(value: str | None, default: bool = False) -> bool:
    """Parse boolean env var (true/1/yes = True, else default)."""
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes")


def _parse_priorities(value: str | None, default: frozenset) -> frozenset:
    """Parse comma-separated priorities into frozenset."""
    if value is None:
        return default
    return frozenset(p.strip().upper() for p in value.split(",") if p.strip())


def _parse_int(value: str | None, default: int | None) -> int | None:
    """Parse integer env var, return default if invalid."""
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_reviews(value: str | None, default: list) -> list:
    """Parse comma-separated review types into list."""
    if value is None:
        return default
    return [r.strip() for r in value.split(",") if r.strip()]


# Default blocking priorities: P0 and P1 block completion
BLOCK_PRIORITIES: frozenset = _parse_priorities(
    os.environ.get("FORMALTASK_BLOCK_PRIORITIES"),
    frozenset({FindingPriority.P0, FindingPriority.P1}),
)

# Max low-priority (non-blocking) findings before blocking (None = unlimited)
MAX_LOW_PRIORITY_FINDINGS: int | None = _parse_int(
    os.environ.get("FORMALTASK_MAX_LOW_FINDINGS"), None
)

# Whether PR is required for task completion
REQUIRE_PR: bool = _parse_bool(os.environ.get("FORMALTASK_REQUIRE_PR"), False)

# Whether PR must be merged for task completion
REQUIRE_PR_MERGED: bool = _parse_bool(os.environ.get("FORMALTASK_REQUIRE_PR_MERGED"), False)

# Whether to check review freshness (stale review check)
CHECK_FRESHNESS: bool = _parse_bool(os.environ.get("FORMALTASK_CHECK_FRESHNESS"), True)

# Whether to check documentation_required metadata
CHECK_DOCS: bool = _parse_bool(os.environ.get("FORMALTASK_CHECK_DOCS"), True)

# Whether to check learnings metadata
CHECK_LEARNINGS: bool = _parse_bool(os.environ.get("FORMALTASK_CHECK_LEARNINGS"), False)

# Whether to check acceptance criteria commands (Task #2860)
CHECK_AC: bool = _parse_bool(os.environ.get("FORMALTASK_CHECK_AC"), True)

# Required review types for completion
REQUIRED_REVIEWS: list = _parse_reviews(
    os.environ.get("FORMALTASK_REQUIRED_REVIEWS"), ["acceptance"]
)
