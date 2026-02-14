"""Tests for WorkerInstructionBuilder verification commands section (Task #2860).

Tests AC verification commands formatting in worker instructions.
Tests review invocation prompt includes acceptance criteria.
"""


class TestWorkerInstructionBuilderVerificationCommands:
    """Test verification commands section in WorkerInstructionBuilder."""

    def test_includes_verification_section_when_criteria_have_commands(self):
        """for_task_start includes verification section when criteria have commands (AC c-5)."""
        from formaltask.workers.instructions import WorkerInstructionBuilder

        builder = WorkerInstructionBuilder()
        task_context = {
            "id": 1,
            "title": "Test task",
            "acceptance_criteria": [
                {"text": "test criterion 1", "command": "exit 0"},
                {"text": "test criterion 2", "command": "pytest tests/"},
            ],
        }

        result = builder.for_task_start(task_context)

        assert "## Acceptance Verification Commands" in result

    def test_lists_each_command_with_criterion_text(self):
        """Verification section lists each command with its criterion text (AC c-6)."""
        from formaltask.workers.instructions import WorkerInstructionBuilder

        builder = WorkerInstructionBuilder()
        task_context = {
            "id": 1,
            "title": "Test task",
            "acceptance_criteria": [
                {"text": "Files must be valid JSON", "command": "python -c 'import json'"},
                {"text": "Tests pass", "command": "pytest tests/"},
            ],
        }

        result = builder.for_task_start(task_context)

        # Check that criterion text and command are shown together
        assert "Files must be valid JSON" in result
        assert "python -c 'import json'" in result
        assert "Tests pass" in result
        assert "pytest tests/" in result

    def test_no_verification_section_when_no_commands(self):
        """No verification section when criteria lack command fields (AC c-7)."""
        from formaltask.workers.instructions import WorkerInstructionBuilder

        builder = WorkerInstructionBuilder()
        task_context = {
            "id": 1,
            "title": "Test task",
            "acceptance_criteria": [
                {"text": "manual check 1"},
                {"text": "manual check 2", "command": None},
            ],
        }

        result = builder.for_task_start(task_context)

        assert "## Acceptance Verification Commands" not in result

    def test_mixed_criteria_only_shows_commands(self):
        """Verification section only shows criteria that have commands."""
        from formaltask.workers.instructions import WorkerInstructionBuilder

        builder = WorkerInstructionBuilder()
        task_context = {
            "id": 1,
            "title": "Test task",
            "acceptance_criteria": [
                {"text": "manual check"},
                {"text": "auto check", "command": "exit 0"},
            ],
        }

        result = builder.for_task_start(task_context)

        assert "## Acceptance Verification Commands" in result
        assert "auto check" in result
        assert "exit 0" in result
        # The manual check should be in acceptance criteria section but not verification section
        lines_after_verification = result.split("## Acceptance Verification Commands")[1]
        assert "manual check" not in lines_after_verification.split("##")[0]

    def test_criteria_text_extracted_from_dict_format(self):
        """Acceptance criteria text is extracted correctly from dict format."""
        from formaltask.workers.instructions import WorkerInstructionBuilder

        builder = WorkerInstructionBuilder()
        task_context = {
            "id": 1,
            "title": "Test task",
            "acceptance_criteria": [
                {"text": "criterion from dict"},
            ],
        }

        result = builder.for_task_start(task_context)

        # Acceptance criteria section should show text
        assert "- criterion from dict" in result


class TestReviewInvocationIncludesCriteria:
    """Test that review invocation prompts include acceptance criteria."""

    def _extract_invocation_block(self, output: str, agent_name: str) -> str:
        """Extract the Task() invocation code block for a specific agent."""
        lines = output.split("\n")
        in_block = False
        block_lines = []
        for line in lines:
            if in_block:
                block_lines.append(line)
                if ")" in line:
                    break
            elif f'subagent_type="{agent_name}"' in line:
                in_block = True
                block_lines.append(line)
                if line.rstrip().endswith(")"):
                    break
        return "\n".join(block_lines)

    def test_acceptance_invocation_includes_criteria(self):
        """Acceptance reviewer Task() invocation contains criteria in prompt."""
        from formaltask.workers.instructions import WorkerInstructionBuilder

        builder = WorkerInstructionBuilder()
        task_context = {
            "id": 42,
            "title": "Fix auth flow",
            "acceptance_criteria": [
                {"text": "Login returns JWT token"},
                {"text": "Invalid creds return 401"},
            ],
            "metadata": {"required_reviews": ["acceptance"]},
        }

        result = builder.for_task_start(task_context)
        invocation = self._extract_invocation_block(result, "acceptance-verifier")

        assert "Login returns JWT token" in invocation
        assert "Invalid creds return 401" in invocation

    def test_acceptance_invocation_includes_string_criteria(self):
        """Acceptance reviewer works with plain string criteria too."""
        from formaltask.workers.instructions import WorkerInstructionBuilder

        builder = WorkerInstructionBuilder()
        task_context = {
            "id": 7,
            "title": "Add cache layer",
            "acceptance_criteria": ["Cache hit returns 200", "Cache miss calls upstream"],
            "metadata": {"required_reviews": ["acceptance"]},
        }

        result = builder.for_task_start(task_context)
        invocation = self._extract_invocation_block(result, "acceptance-verifier")

        assert "Cache hit returns 200" in invocation
        assert "Cache miss calls upstream" in invocation

    def test_non_acceptance_review_unaffected(self):
        """Code-quality reviewer invocation doesn't inject criteria into prompt."""
        from formaltask.workers.instructions import WorkerInstructionBuilder

        builder = WorkerInstructionBuilder()
        task_context = {
            "id": 10,
            "title": "Refactor DB",
            "acceptance_criteria": [{"text": "Unique criterion text xyz123"}],
            "metadata": {"required_reviews": ["code-quality"]},
        }

        result = builder.for_task_start(task_context)
        invocation = self._extract_invocation_block(result, "code-reviewer")

        assert "Unique criterion text xyz123" not in invocation
