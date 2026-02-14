"""Tests for task_assignment.md.j2 template rendering."""

import pytest

from formaltask.workers.instructions import WorkerInstructionBuilder


@pytest.fixture()
def builder():
    """Create a WorkerInstructionBuilder for testing."""
    return WorkerInstructionBuilder()


class TestRenderWithCriteria:
    """Test task assignment rendering with acceptance criteria."""

    def test_render_with_criteria(self, builder):
        """Criteria render as bullet list with dict and string support."""
        task_context = {
            "id": 42,
            "title": "Add login feature",
            "acceptance_criteria": [
                {"text": "Login page exists"},
                "Tests pass",
            ],
        }

        result = builder._build_task_assignment(task_context)

        assert "<task_assignment>" in result
        assert "# Task #42: Add login feature" in result
        assert "**SCOPE: This task only." in result
        assert "## Acceptance Criteria" in result
        assert "- Login page exists" in result
        assert "- Tests pass" in result
        assert "</task_assignment>" in result

    def test_render_with_criteria_and_verification_commands(self, builder):
        """Criteria with commands include verification section."""
        task_context = {
            "id": 42,
            "title": "Add login feature",
            "acceptance_criteria": [
                {"text": "Login page exists", "command": "test -f login.html"},
            ],
        }

        result = builder._build_task_assignment(task_context)

        assert "## Acceptance Verification Commands" in result
        assert "- **Login page exists**" in result
        assert "  test -f login.html" in result


class TestRenderWithSkills:
    """Test task assignment rendering with skills."""

    def test_render_with_skills(self, builder):
        """Skills render as recommended skill invocations."""
        task_context = {
            "id": 42,
            "title": "Add login feature",
            "skills": ["test-driven-development", "debugging"],
        }

        result = builder._build_task_assignment(task_context)

        assert "## Recommended Skills" in result
        assert "Invoke these skills when relevant to your work:" in result
        assert "- `/test-driven-development` - invoke when needed" in result
        assert "- `/debugging` - invoke when needed" in result

    def test_render_without_skills_omits_section(self, builder):
        """No skills section when skills list is empty."""
        task_context = {
            "id": 42,
            "title": "Add login feature",
            "skills": [],
        }

        result = builder._build_task_assignment(task_context)

        assert "## Recommended Skills" not in result


class TestRenderWithArtifact:
    """Test task assignment rendering with artifact content."""

    def test_render_with_artifact(self, builder):
        """Artifact content renders as PRP section."""
        task_context = {
            "id": 42,
            "title": "Add login feature",
            "artifact_content": "Build a login page with OAuth.",
            "artifact_type": "PRP",
        }

        result = builder._build_task_assignment(task_context)

        assert "## PRP" in result
        assert "Build a login page with OAuth." in result
        assert "## Description" not in result

    def test_render_with_description_no_artifact(self, builder):
        """Description renders when no artifact content."""
        task_context = {
            "id": 42,
            "title": "Add login feature",
            "description": "Implement the login feature.",
        }

        result = builder._build_task_assignment(task_context)

        assert "## Description" in result
        assert "Implement the login feature." in result
        assert "## PRP" not in result

    def test_render_artifact_default_type(self, builder):
        """Artifact type defaults to PRP when not specified."""
        task_context = {
            "id": 42,
            "title": "Add login feature",
            "artifact_content": "Build a login page.",
        }

        result = builder._build_task_assignment(task_context)

        assert "## PRP" in result


class TestRenderFullOutput:
    """Test that template produces identical output to Python implementation."""

    def test_full_output_matches(self, builder):
        """Full rendering with all sections matches expected format."""
        task_context = {
            "id": 99,
            "title": "Complex Task",
            "acceptance_criteria": [
                {"text": "First criterion", "command": "pytest tests/"},
                {"text": "Second criterion"},
                "Third criterion as string",
            ],
            "description": "Should be ignored when artifact exists.",
            "artifact_content": "Detailed PRP content here.",
            "artifact_type": "spec",
            "skills": ["reviewing-code", "debugging"],
        }

        result = builder._build_task_assignment(task_context)

        expected_lines = [
            "<task_assignment>",
            "# Task #99: Complex Task",
            "",
            "**SCOPE: This task only. Other PRP tasks are context, not assignments.**",
            "",
            "## Acceptance Criteria",
            "- First criterion",
            "- Second criterion",
            "- Third criterion as string",
            "",
            "## Acceptance Verification Commands",
            "",
            "These commands will be run to verify your work passes:",
            "",
            "- **First criterion**",
            "  ```",
            "  pytest tests/",
            "  ```",
            "",
            "## spec",
            "Detailed PRP content here.",
            "",
            "## Recommended Skills",
            "Invoke these skills when relevant to your work:",
            "- `/reviewing-code` - invoke when needed",
            "- `/debugging` - invoke when needed",
            "</task_assignment>",
        ]
        expected = "\n".join(expected_lines)
        assert result == expected
