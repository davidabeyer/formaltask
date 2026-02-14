"""Shared audit tracking utilities for auditing-* and hunting-* skills.

Scripts (called via bash from skills):
    parse_status.py  - Load and display tracker progress
    create_tracker.py - Generate new tracker file (manual, one-time)

Usage from skills:
    python3 ~/.claude/skills/_audit_tracker/parse_status.py STYLE
    python3 ~/.claude/skills/_audit_tracker/create_tracker.py --skill=style --target=formaltask/
"""

from pathlib import Path

# Tracker file naming convention
TRACKER_SUFFIX = "_AUDIT.md"

# Status markers
STATUS_PENDING = " "
STATUS_IN_PROGRESS = "~"
STATUS_AUDITED = "x"
STATUS_FIXED = "S"
STATUS_PARTIAL = "P"
STATUS_DELETED = "D"

STATUS_LABELS = {
    STATUS_PENDING: "Pending",
    STATUS_IN_PROGRESS: "In Progress",
    STATUS_AUDITED: "Audited (no changes)",
    STATUS_FIXED: "Fixed/Simplified",
    STATUS_PARTIAL: "Partial",
    STATUS_DELETED: "Deleted/Major reduction",
}


def get_tracker_path(skill_name: str, project_root: Path | None = None) -> Path:
    """Get tracker file path for a skill.

    Convention: {PROJECT_ROOT}/{SKILL_NAME}_AUDIT.md
    Example: ~/formaltask/STYLE_AUDIT.md for auditing-style
    """
    if project_root is None:
        project_root = Path.home() / "formaltask"

    # Convert skill name to tracker name
    # auditing-style -> STYLE
    # hunting-dead-code -> DEAD_CODE
    name = skill_name.replace("auditing-", "").replace("hunting-", "")
    name = name.upper().replace("-", "_")

    return project_root / f"{name}{TRACKER_SUFFIX}"
