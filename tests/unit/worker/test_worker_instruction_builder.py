"""Tests for WorkerInstructionBuilder.

Task #2056: Create WorkerInstructionBuilder class.
"""

import pytest

from formaltask.workers.instructions import WorkerInstructionBuilder


@pytest.fixture
def builder():
    """WorkerInstructionBuilder with no config."""
    return WorkerInstructionBuilder()


@pytest.fixture
def basic_task_context():
    """Minimal task context for tests."""
    return {"id": 42, "title": "Test Task"}


class TestForTaskStart:
    """Tests for for_task_start method."""

    def test_returns_combined_sections(self, builder, basic_task_context):
        """Should return combined task assignment, methodology, quality, escalation."""
        result = builder.for_task_start(basic_task_context)

        assert "<task_assignment>" in result
        assert "<methodology>" in result
        assert "<quality_standards>" in result
        assert "<escalation_protocol>" in result


class TestForTaskStartTaskAssignment:
    """Tests for task assignment content via for_task_start method."""

    def test_includes_xml_tags_and_scope_warning(self, builder, basic_task_context):
        """Should return XML-formatted task assignment section with scope warning."""
        result = builder.for_task_start(basic_task_context)

        assert "<task_assignment>" in result
        assert "</task_assignment>" in result
        assert "# Task #42: Test Task" in result
        assert "**SCOPE: This task only." in result

    def test_with_acceptance_criteria(self, builder):
        """Should include acceptance criteria when provided."""
        task_context = {
            "id": 42,
            "title": "Test Task",
            "acceptance_criteria": ["Criterion 1", "Criterion 2"],
        }

        result = builder.for_task_start(task_context)

        assert "## Acceptance Criteria" in result
        assert "- Criterion 1" in result
        assert "- Criterion 2" in result

    def test_with_artifact_content(self, builder):
        """Should include spec content and omit description."""
        task_context = {
            "id": 42,
            "title": "Test Task",
            "description": "Task description",
            "artifact_content": "Spec content here",
            "artifact_type": "spec",
        }

        result = builder.for_task_start(task_context)

        assert "## spec" in result
        assert "Spec content here" in result
        assert "## Description" not in result


class TestForTaskStartQualityStandards:
    """Tests for quality standards content via for_task_start method."""

    def test_includes_testing_antipatterns(self, builder, basic_task_context):
        """Should return XML-formatted quality standards with testing antipatterns."""
        result = builder.for_task_start(basic_task_context)

        assert "<quality_standards>" in result
        assert "</quality_standards>" in result
        assert "Testing Anti-Patterns" in result
        assert "Mock abuse" in result


class TestForTaskStartScopeConstraints:
    """Tests for scope constraints content via for_task_start method (Task #2057)."""

    def test_for_task_start_ends_with_scope_constraints(self, builder, basic_task_context):
        """for_task_start should end with scope_constraints section."""
        result = builder.for_task_start(basic_task_context)

        assert result.strip().endswith("</scope_constraints>")


class TestForTaskStartTaskIdParameter:
    """Tests for task_id parameter in for_task_start (Task #2240)."""

    def test_uses_task_id_in_completion_workflow(self, builder, basic_task_context):
        """for_task_start should include task_id in completion workflow commands."""
        result = builder.for_task_start(basic_task_context, task_id=42)

        # Should include concrete task complete command with task ID
        assert "task complete 42" in result

    def test_falls_back_to_context_id_when_task_id_not_provided(self, builder):
        """for_task_start should use context id when task_id not provided."""
        task_context = {"id": 99, "title": "Test Task"}

        result = builder.for_task_start(task_context)

        # Should fall back to context id
        assert "task complete 99" in result


class TestCompletionWorkflow:
    """Tests for _build_completion_workflow method (Task #2240)."""

    def test_completion_workflow_includes_explicit_command(self, builder):
        """_build_completion_workflow should include explicit task complete command."""
        result = builder._build_completion_workflow(task_id=42)

        assert "python3 -m formaltask.cli.pm task complete 42" in result

    def test_completion_workflow_includes_review_loop_instructions(self, builder):
        """_build_completion_workflow should include review-fix-loop instructions."""
        result = builder._build_completion_workflow(task_id=42)

        # Should explain the review-fix loop
        assert "review" in result.lower()
        assert "fix" in result.lower() or "wontfix" in result.lower()
        # Template says "go back to Validate Findings" for the loop
        assert "go back" in result.lower() or "loop" in result.lower()

    def test_completion_workflow_includes_task_complete_command(self, builder):
        """_build_completion_workflow should include task complete command."""
        result = builder._build_completion_workflow(task_id=42)

        # Should include the task complete CLI command
        assert "task complete 42" in result

    def test_completion_workflow_does_not_say_stop_working(self, builder):
        """_build_completion_workflow should NOT say 'stop working' or 'automatically'."""
        result = builder._build_completion_workflow(task_id=42)

        # Must NOT contain misleading language
        assert "simply stop working" not in result.lower()
        assert "complete the task automatically" not in result.lower()

    def test_for_task_start_scope_constraints_includes_task_id(self, builder, basic_task_context):
        """for_task_start scope_constraints should include task ID."""
        result = builder.for_task_start(basic_task_context)

        assert "Task #42" in result


class TestForTaskStartSkillsInjection:
    """Tests for skills injection in for_task_start method."""

    def test_includes_skills_section_when_skills_present(self, builder):
        """for_task_start should include skills section when skills are in context."""
        task_context = {
            "id": 42,
            "title": "Test Task",
            "skills": ["error-debugger", "root-cause-tracing"],
        }

        result = builder.for_task_start(task_context)

        assert "## Recommended Skills" in result
        # Natural language instruction to invoke skills
        assert "error-debugger" in result
        assert "root-cause-tracing" in result
        assert "invoke" in result.lower() or "/error-debugger" in result

    def test_omits_skills_section_when_skills_empty(self, builder):
        """for_task_start should omit skills section when skills list is empty."""
        task_context = {
            "id": 42,
            "title": "Test Task",
            "skills": [],
        }

        result = builder.for_task_start(task_context)

        assert "## Recommended Skills" not in result


class TestCompletionWorkflowRequiredReviews:
    """Tests for required_reviews parameter in _build_completion_workflow (Task #2686).

    These regression tests verify behavioral parity after refactoring from Jinja2
    to string replacement.
    """

    def test_no_reviews_excludes_review_phases(self, builder):
        """Verify required_reviews=[] excludes review loop sections."""
        result = builder._build_completion_workflow(123, None, [])

        # Review sections should NOT be present
        assert "### Run Required Reviews" not in result
        assert "### Validate Findings" not in result
        assert "### Address Valid Findings" not in result
        assert "### Commit Fixes" not in result
        assert "### Verify Fixes" not in result
        # Always-present sections should still be there
        assert "Complete Task" in result
        assert "Create PR" in result

    def test_with_reviews_includes_review_phases(self, builder):
        """Verify required_reviews=["code-quality"] includes review loop sections."""
        result = builder._build_completion_workflow(123, None, ["code-quality"])

        # Review sections should be present
        assert "### Run Required Reviews" in result
        assert "Required review types: code-quality" in result
        assert "### Verify Fixes" in result

    def test_default_reviews_is_empty_when_not_provided(self, builder):
        """Verify required_reviews=None defaults to empty list (no reviews)."""
        result_none = builder._build_completion_workflow(123, None, None)
        result_empty = builder._build_completion_workflow(123, None, [])

        # Both should NOT include review sections (no reviews configured)
        assert "### Run Required Reviews" not in result_none
        assert "### Run Required Reviews" not in result_empty
        # Behavior should match between None and empty list
        assert ("### Run Required Reviews" in result_none) == (
            "### Run Required Reviews" in result_empty
        )

    def test_multiple_review_types_rendered(self, builder):
        """Verify multiple review types are comma-joined in output."""
        result = builder._build_completion_workflow(123, None, ["code-quality", "acceptance"])

        assert "code-quality, acceptance" in result

    def test_task_id_rendered_in_commands(self, builder):
        """Verify task_id appears in CLI commands."""
        result = builder._build_completion_workflow(123, None, ["code-quality"])

        # Task ID should appear in task complete command
        assert "task complete 123" in result

    def test_base_flag_rendered_for_feature_branch(self, builder):
        """Verify --base flag appears when target_branch is set."""
        result = builder._build_completion_workflow(123, "feature-x", ["code-quality"])

        assert "--base feature-x" in result

    def test_spec_critique_uses_skill_invocation(self, builder):
        """Verify spec-critique uses Skill invocation from REVIEW_TYPE_AGENTS (Task #2831)."""
        result = builder._build_completion_workflow(123, None, ["spec-critique"])

        # Should use Skill("critique", ...) from REVIEW_TYPE_AGENTS, not hardcoded code-reviewer
        assert 'Skill("critique"' in result
        # Should NOT have the old hardcoded code-reviewer from review_loop.md template
        assert 'subagent_type="code-reviewer"' not in result

    def test_code_quality_uses_task_invocation(self, builder):
        """Verify code-quality uses Task invocation from REVIEW_TYPE_AGENTS (Task #2831)."""
        result = builder._build_completion_workflow(123, None, ["code-quality"])

        # Should use Task(subagent_type="code-reviewer") from REVIEW_TYPE_AGENTS
        assert 'subagent_type="code-reviewer"' in result


class TestWorkerContextFtLearning:
    """Integration tests for ft learning documentation in worker context (Task #2686)."""

    def test_worker_context_includes_ft_learning_docs(self, builder):
        """Verify ft learning documentation appears in worker context."""
        task_context = {"id": 123, "title": "Test Task"}

        result = builder.for_task_start(task_context, task_id=123)

        # "Capture learnings" step should be in required todos
        assert "Capture learnings" in result


class TestWorkInstructionBuilderWithConfig:
    """Tests for WorkerInstructionBuilder with CompletionConfig (Task #2821)."""

    def test_accepts_config_param_in_init(self):
        """WorkerInstructionBuilder should accept config parameter in __init__."""
        from formaltask.core.completion_config import CompletionConfig

        config = CompletionConfig(
            required_reviews=["code-quality", "security"],
            check_freshness=True,
            require_pr=False,
            require_pr_merged=False,
            documentation_required=False,
            check_docs=True,
            check_learnings=False,
            check_ac=True,
        )

        builder = WorkerInstructionBuilder(config=config)

        assert builder._config == config

    def test_uses_config_required_reviews_in_completion_workflow(self):
        """_build_completion_workflow should use self._config.required_reviews."""
        from formaltask.core.completion_config import CompletionConfig

        config = CompletionConfig(
            required_reviews=["code-quality", "security", "acceptance"],
            check_freshness=True,
            require_pr=False,
            require_pr_merged=False,
            documentation_required=False,
            check_docs=True,
            check_learnings=False,
            check_ac=True,
        )

        builder = WorkerInstructionBuilder(config=config)

        result = builder._build_completion_workflow(task_id=42)

        assert "code-quality, security, acceptance" in result

    def test_no_hardcoded_fallback_used(self):
        """Config with empty reviews should NOT fall back to code-quality."""
        from formaltask.core.completion_config import CompletionConfig

        config = CompletionConfig(
            required_reviews=[],  # Empty - no reviews required
            check_freshness=True,
            require_pr=False,
            require_pr_merged=False,
            documentation_required=False,
            check_docs=True,
            check_learnings=False,
            check_ac=True,
        )

        builder = WorkerInstructionBuilder(config=config)

        result = builder._build_completion_workflow(task_id=42)

        # Should NOT include review sections when reviews is empty
        assert "### Run Required Reviews" not in result
        assert "code-quality" not in result


class TestPromptTemplateRendering:
    """Tests for prompt_template Jinja2 rendering in for_task_start (Task #2876)."""

    def test_renders_prompt_template_when_present_in_metadata(self, builder):
        """for_task_start should render prompt_template with Jinja2 when present."""
        task_context = {
            "id": 42,
            "title": "Test Task",
            "metadata": {"prompt_template": "Hello {{ title }}"},
        }

        result = builder.for_task_start(task_context)

        assert "Hello Test Task" in result

    def test_uses_build_sections_when_no_prompt_template(self, builder):
        """for_task_start should use _build_* sections when no prompt_template."""
        task_context = {
            "id": 42,
            "title": "Test Task",
            "metadata": {},
        }

        result = builder.for_task_start(task_context)

        # Standard sections should be present (fallback behavior)
        assert "<task_assignment>" in result
        assert "<methodology>" in result
        assert "<quality_standards>" in result
        # No rendered template content since prompt_template not provided
        assert "Hello" not in result

    def test_fallback_to_build_sections_on_undefined_error(self, builder):
        """for_task_start should fallback to _build_* flow on UndefinedError."""
        task_context = {
            "id": 42,
            "title": "Test Task",
            "metadata": {"prompt_template": "Hello {{ undefined_variable }}"},
        }

        # Should NOT raise, should fallback gracefully
        result = builder.for_task_start(task_context)

        # Standard sections should be present (fallback behavior)
        assert "<task_assignment>" in result
        assert "<methodology>" in result

    def test_fallback_to_build_sections_on_syntax_error(self, builder):
        """for_task_start should fallback to _build_* flow on TemplateSyntaxError."""
        task_context = {
            "id": 42,
            "title": "Test Task",
            "metadata": {"prompt_template": "Hello {{ unclosed"},
        }

        # Should NOT raise, should fallback gracefully
        result = builder.for_task_start(task_context)

        # Standard sections should be present (fallback behavior)
        assert "<task_assignment>" in result
        assert "<methodology>" in result

    def test_template_context_includes_all_task_fields(self, builder):
        """Template context should include title, description, criteria, metadata, etc."""
        task_context = {
            "id": 99,
            "title": "My Task",
            "description": "Task description here",
            "acceptance_criteria": ["Criterion A", "Criterion B"],
            "artifact_content": "Artifact content",
            "skills": ["skill-one"],
            "metadata": {
                "prompt_template": "ID:{{ id }} T:{{ title }} D:{{ description }} "
                "AC:{% for c in acceptance_criteria %}{{ c }};{% endfor %} "
                "ART:{{ artifact_content }} "
                "SKILLS:{% for s in skills %}{{ s }};{% endfor %} "
                "META:{{ metadata.custom_key }}",
                "custom_key": "custom_value",
            },
        }

        result = builder.for_task_start(task_context)

        # All context fields should be rendered
        assert "ID:99" in result
        assert "T:My Task" in result
        assert "D:Task description here" in result
        assert "AC:Criterion A;Criterion B;" in result
        assert "ART:Artifact content" in result
        assert "SKILLS:skill-one;" in result
        assert "META:custom_value" in result
