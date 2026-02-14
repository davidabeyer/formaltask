"""Tests for Jinja2 render() usage in instructions.py."""

from formaltask.workers.instructions import WorkerInstructionBuilder


def test_instructions_jinja_rendering():
    """Verify _build_completion_workflow renders template variables correctly.

    Tests behavior: task_id appears in output, no raw {{ }} placeholders remain.
    """
    builder = WorkerInstructionBuilder()

    result = builder._build_completion_workflow(
        task_id=42,
        target_branch=None,
        required_reviews=["code-quality"],
    )

    # Verify task_id is rendered in output
    assert "42" in result, "Output should contain rendered task_id '42'"
    assert "task-42" in result, "Output should contain 'task-42' in commit command"

    # Verify no raw Jinja placeholders remain
    assert "{{ task_id }}" not in result, "Raw {{ task_id }} placeholder should not appear"
    assert "{{ required_todos }}" not in result, "Raw {{ required_todos }} should not appear"
    assert "{{ review_section }}" not in result, "Raw {{ review_section }} should not appear"
    assert "{{ base_flag }}" not in result, "Raw {{ base_flag }} should not appear"
    assert (
        "{{ review_feedback_issue }}" not in result
    ), "Raw {{ review_feedback_issue }} should not appear"

    # Verify review content is included when reviews are required
    assert "code-quality" in result, "Output should mention required review type"
