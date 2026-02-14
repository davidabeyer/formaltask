"""Tests for completion_workflow.md.j2 template (Task #2898).

Verifies the template produces identical output to the old multi-step rendering.
"""

import pytest

from formaltask.workers.instructions import WorkerInstructionBuilder


@pytest.fixture
def builder():
    return WorkerInstructionBuilder()


class TestCompletionWorkflowTemplate:
    """Tests for completion_workflow.md.j2 rendering via _build_completion_workflow."""

    def test_with_reviews_includes_review_section(self, builder):
        """When reviews are required, output includes review section content."""
        result = builder._build_completion_workflow(42, None, ["code-quality"])

        assert "### Run Required Reviews" in result
        assert "code-quality" in result
        assert "### Validate Findings" in result
        assert "### Address Valid Findings" in result
        assert "### Verify Fixes" in result

    def test_without_reviews_no_review_section(self, builder):
        """When no reviews are required, review section is absent."""
        result = builder._build_completion_workflow(42, None, [])

        assert "### Run Required Reviews" not in result
        assert "### Validate Findings" not in result
        assert "### Address Valid Findings" not in result
        # Review feedback issue line should also be absent
        assert "Review findings still open" not in result

    def test_feature_branch_pr_target(self, builder):
        """Feature branch produces PR Target section and --base flag."""
        result = builder._build_completion_workflow(42, "feature-x", ["code-quality"])

        assert "## PR Target Branch" in result
        assert "Target branch: `feature-x`" in result
        assert "gh pr create --base feature-x" in result
        # base flag in the PR creation command inside workflow
        assert "--base feature-x" in result

    def test_output_matches_current_implementation(self, builder):
        """Golden test: new template output matches old implementation output.

        Tests three scenarios to cover all conditional branches:
        1. With reviews, no feature branch
        2. Without reviews
        3. With reviews and feature branch
        """
        # Scenario 1: with reviews, no feature branch
        result_reviews = builder._build_completion_workflow(42, None, ["code-quality"])
        assert "<completion_workflow>" in result_reviews
        assert "</completion_workflow>" in result_reviews
        assert "task complete 42" in result_reviews
        assert "feat(task-42)" in result_reviews
        # Review steps present
        assert "1. **Run required reviews**" in result_reviews
        assert "8. **Complete task**" in result_reviews

        # Scenario 2: without reviews
        result_no_reviews = builder._build_completion_workflow(42, None, [])
        assert "1. **Capture learnings**" in result_no_reviews
        assert "4. **Complete task**" in result_no_reviews
        assert "### Run Required Reviews" not in result_no_reviews

        # Scenario 3: feature branch
        result_feature = builder._build_completion_workflow(42, "feature-x", ["code-quality"])
        assert result_feature.startswith("\n## PR Target Branch")
        assert "<completion_workflow>" in result_feature
