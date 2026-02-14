"""Golden tests for WorkerInstructionBuilder Jinja2 template output.

Captures expected output for standard task contexts to detect regressions
from the Jinja2 refactor. Fails if output changes (whitespace, ordering,
missing sections).
"""

from pathlib import Path

import pytest

from formaltask.workers.instructions import WorkerInstructionBuilder

GOLDEN_DIR = Path(__file__).parent / "golden"

# Standard task context matching spec: id=42, typical values
STANDARD_TASK_CONTEXT = {
    "id": 42,
    "title": "Add authentication",
    "acceptance_criteria": [
        {"text": "Login endpoint returns JWT token", "command": "pytest tests/test_auth.py -v"},
        {
            "text": "Password hashing uses bcrypt",
            "command": 'python3 -c "from auth import hash_password; assert hash_password("test")"',
        },
        {
            "text": "Rate limiting on login attempts",
            "command": "pytest tests/test_rate_limit.py -v",
        },
    ],
    "description": "Implement user authentication with JWT tokens and bcrypt password hashing.",
    "artifact_content": "title: Add authentication\nsummary: Implement auth flow",
    "skills": ["test-driven-development"],
    "metadata": {"required_reviews": ["code-quality", "security"]},
}


def _load_golden(name: str) -> str:
    return (GOLDEN_DIR / name).read_text()


@pytest.mark.golden
class TestGoldenOutput:
    """Golden tests verifying Jinja2 templates produce expected output."""

    def test_for_task_start_golden_output(self):
        """Full for_task_start output matches golden expected output."""
        builder = WorkerInstructionBuilder()
        actual = builder.for_task_start(STANDARD_TASK_CONTEXT)
        expected = _load_golden("task_start.golden")
        assert actual == expected

    def test_task_assignment_golden(self):
        """Task assignment template output matches golden expected output."""
        builder = WorkerInstructionBuilder()
        actual = builder._build_task_assignment(STANDARD_TASK_CONTEXT)
        expected = _load_golden("task_assignment.golden")
        assert actual == expected


@pytest.mark.golden
class TestEdgeCases:
    """Edge case tests to prevent regressions."""

    def test_empty_acceptance_criteria(self):
        """Empty criteria list should not crash."""
        builder = WorkerInstructionBuilder()
        ctx = {**STANDARD_TASK_CONTEXT, "acceptance_criteria": []}
        result = builder.for_task_start(ctx)
        assert "# Task #42: Add authentication" in result
        assert "## Acceptance Criteria" not in result

    def test_none_description(self):
        """None description should not crash."""
        builder = WorkerInstructionBuilder()
        ctx = {**STANDARD_TASK_CONTEXT, "description": None}
        result = builder.for_task_start(ctx)
        assert "# Task #42: Add authentication" in result

    def test_special_chars_in_title(self):
        """Title with {{ }} should not break Jinja."""
        builder = WorkerInstructionBuilder()
        ctx = {**STANDARD_TASK_CONTEXT, "title": "Fix {{ template }} rendering"}
        result = builder.for_task_start(ctx)
        assert "# Task #42: Fix {{ template }} rendering" in result

    def test_context_none_handling(self):
        """None context uses defaults."""
        builder = WorkerInstructionBuilder()
        result = builder.for_task_start(None)
        assert "# Task #?: Unknown Task" in result
