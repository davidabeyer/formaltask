"""Integration tests for task templates end-to-end flow.

Task #2834: Validates complete flow from template loading to worker instructions.
Tests that:
1. Template loading works (Task 1)
2. REVIEW_TYPE_AGENTS has invocation field (Task 2)
3. WorkerInstructionBuilder uses data-driven instructions (Task 3)
4. review_loop.md is deleted (Task 4)
5. epic_decompose.py is slimmed (Task 5)
"""

from pathlib import Path

from formaltask.workers.instructions import TEMPLATES_DIR, WorkerInstructionBuilder


def test_spec_review_task_end_to_end(tmp_path, monkeypatch):
    """Full flow: template -> metadata -> instructions -> correct invocation.

    Validates the complete integration of:
    - Template loading from YAML
    - REVIEW_TYPE_AGENTS configuration
    - WorkerInstructionBuilder using data-driven invocations
    - review_loop.md deletion
    """
    # 1. Create template file in temp directory
    template_dir = tmp_path / "task-templates"
    template_dir.mkdir(parents=True)
    (template_dir / "spec-review.yaml").write_text(
        "require_pr: false\nrequired_reviews:\n  - spec-critique\n"
    )

    # Override FORMALTASK_TEMPLATES_DIR for the loader
    monkeypatch.setenv("FORMALTASK_TEMPLATES_DIR", str(template_dir))

    # Re-import to pick up env var change (TEMPLATES_DIR is evaluated at import time)
    import importlib

    import formaltask.utils.template_loader as template_loader_module

    importlib.reload(template_loader_module)

    # 2. Load template and verify metadata
    template = template_loader_module.load_template("spec-review")
    assert template["require_pr"] is False
    assert template["required_reviews"] == ["spec-critique"]

    # 3. Build instructions with template metadata
    builder = WorkerInstructionBuilder()
    task_context = {
        "id": 42,
        "title": "Test spec review task",
        "metadata": {"required_reviews": template["required_reviews"]},
    }
    instructions = builder.for_task_start(task_context=task_context, task_id=42)

    # 4. Verify instructions contain Skill("critique", ...) for spec-critique
    assert 'Skill("critique"' in instructions, (
        "spec-critique should use Skill invocation from REVIEW_TYPE_AGENTS"
    )

    # 5. Verify review_loop.md is gone (deleted by Task 4)
    review_loop_path = TEMPLATES_DIR / "completion" / "review_loop.md"
    assert not review_loop_path.exists(), (
        f"review_loop.md should be deleted, but found at {review_loop_path}"
    )


def test_epic_decompose_slimmed():
    """Verify epic_decompose.py is under 280 lines.

    Task #2832: epic_decompose.py should be slimmed by moving template logic elsewhere.
    """
    project_root = Path(__file__).parent.parent.parent
    epic_decompose_path = project_root / "formaltask" / "cli" / "commands" / "epic_decompose.py"

    assert epic_decompose_path.exists(), f"epic_decompose.py not found at {epic_decompose_path}"

    line_count = len(epic_decompose_path.read_text().splitlines())
    assert line_count < 280, f"epic_decompose.py has {line_count} lines, should be < 280"
