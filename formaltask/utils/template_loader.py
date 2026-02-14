"""YAML task template loader.

Loads templates from ~/.claude/task-templates/ for task metadata defaults.
Override with FORMALTASK_TEMPLATES_DIR env var for testing.
"""

import os
from pathlib import Path

import yaml

from formaltask.paths import get_claude_home

TEMPLATES_DIR = Path(
    os.environ.get("FORMALTASK_TEMPLATES_DIR", str(get_claude_home() / "task-templates"))
)


def load_template(name: str) -> dict:
    """Load a YAML template by name.

    Args:
        name: Template name (without .yaml extension)

    Returns:
        Dict with template contents, or {} if not found
    """
    # Prevent path traversal attacks - only allow simple names
    if "/" in name or "\\" in name or ".." in name:
        return {}
    template_path = TEMPLATES_DIR / f"{name}.yaml"
    # Verify resolved path is still under TEMPLATES_DIR
    try:
        template_path.resolve().relative_to(TEMPLATES_DIR.resolve())
    except ValueError:
        return {}
    if not template_path.exists():
        return {}
    return yaml.safe_load(template_path.read_text()) or {}


def merge_template(name: str, metadata: dict) -> dict:
    """Merge template defaults with explicit metadata.

    Explicit metadata values override template defaults.

    Args:
        name: Template name
        metadata: Explicit metadata to merge with template

    Returns:
        Merged dict with explicit values taking precedence
    """
    template = load_template(name)
    return {**template, **metadata}
