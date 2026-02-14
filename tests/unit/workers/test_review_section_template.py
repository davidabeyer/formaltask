"""Tests for REVIEW_TYPE_AGENTS configuration.

Task #2896: Verify review type agent configuration integrity.
"""

from formaltask.utils.schemas import REVIEW_TYPE_AGENTS


def test_invocation_includes_task_id():
    """Every REVIEW_TYPE_AGENTS invocation must contain {{ task_id }} placeholder."""
    missing = [
        key
        for key, config in REVIEW_TYPE_AGENTS.items()
        if "{{ task_id }}" not in config["invocation"]
    ]
    assert not missing, f"Missing task_id placeholder in: {missing}"


def test_invocation_includes_title():
    """Every REVIEW_TYPE_AGENTS invocation must contain {{ title }} placeholder."""
    missing = [
        key
        for key, config in REVIEW_TYPE_AGENTS.items()
        if "{{ title }}" not in config["invocation"]
    ]
    assert not missing, f"Missing title placeholder in: {missing}"
