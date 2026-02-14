"""Worker instruction builder — generates instruction sections for task workers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import TemplateSyntaxError, UndefinedError

logger = logging.getLogger(__name__)

from formaltask.core.rules import render, render_template_file
from formaltask.utils.schemas import REVIEW_TYPE_AGENTS

if TYPE_CHECKING:
    from formaltask.core.completion_config import CompletionConfig

# Template directory for worker instruction sections
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Required workflow steps - single source of truth for template and validator
REVIEW_STEPS = [
    "Run required reviews",
    "Validate findings",
    "Fix findings",
    "Verify fixes",
]
ALWAYS_STEPS = [
    "Capture learnings",
    "Create PR",
    "Merge PR",
    "Complete task",
]

__all__ = [
    "get_required_steps",
    "WorkerInstructionBuilder",
]


def get_required_steps(has_reviews: bool) -> list[str]:
    """Get required workflow steps based on review configuration."""
    if has_reviews:
        return REVIEW_STEPS + ALWAYS_STEPS
    return ALWAYS_STEPS


class WorkerInstructionBuilder:
    """Generates worker instruction sections and review prompts."""

    def __init__(
        self,
        config: CompletionConfig | None = None,
    ):
        """Initialize builder with optional config.

        Args:
            config: CompletionConfig from get_effective_config() (Task #2821).
                   When provided, config.required_reviews is used directly.
        """
        self._config = config

    def for_task_start(
        self,
        task_context: dict | None = None,
        task_id: int | None = None,
        target_branch: str | None = None,
    ) -> str:
        """Build instructions for task start.

        Args:
            task_context: Task context dict with id, title, etc.
            task_id: Explicit task ID for concrete commands. Falls back to context["id"].
            target_branch: Target branch for PR (Task #2428).
        """
        ctx = task_context or {}
        # Resolve task_id: explicit parameter > context id > placeholder
        effective_task_id = task_id if task_id is not None else ctx.get("id")
        # Extract required_reviews from metadata (Task #2625)
        metadata = ctx.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        required_reviews = metadata.get("required_reviews")

        # Check for prompt_template (Task #2876: opt-in Jinja2 rendering)
        prompt_template = metadata.get("prompt_template")
        rendered_template_section = ""
        if prompt_template:
            # Build context dict for template rendering
            template_context = {
                "title": ctx.get("title", ""),
                "description": ctx.get("description", ""),
                "acceptance_criteria": ctx.get("acceptance_criteria", []),
                "metadata": metadata,
                "id": ctx.get("id"),
                "artifact_content": ctx.get("artifact_content", ""),
                "skills": ctx.get("skills", []),
            }
            try:
                rendered_template_section = render(prompt_template, template_context)
            except (UndefinedError, TemplateSyntaxError) as e:
                logger.warning("prompt_template rendering failed, using default: %s", e)
                rendered_template_section = ""

        sections = [
            self._build_task_assignment(ctx),
            self._build_methodology(),
            self._build_review_resolution(),
            self._build_quality_standards(),
            self._build_completion_workflow(
                effective_task_id,
                target_branch,
                required_reviews,
                title=ctx.get("title", ""),
                acceptance_criteria=ctx.get("acceptance_criteria", []),
            ),
            self._build_escalation(),
        ]

        # Conditionally add documentation guidance when documentation_required=true
        if self._is_documentation_required(ctx):
            sections.append(self._build_documentation())

        # Include rendered template at the start if prompt_template was provided
        if rendered_template_section:
            sections.insert(0, rendered_template_section)

        return "\n\n".join(sections) + "\n\n<scope_constraints>\n</scope_constraints>"

    def _build_task_assignment(self, task_context: dict) -> str:
        """Build the task assignment XML section."""
        criteria = task_context.get("acceptance_criteria", [])
        ctx = {
            "id": task_context.get("id", "?"),
            "title": task_context.get("title", "Unknown Task"),
            "acceptance_criteria": criteria,
            "verification_section": self._format_verification_commands(criteria),
            "description": task_context.get("description", ""),
            "artifact_content": task_context.get("artifact_content", ""),
            "artifact_type": task_context.get("artifact_type", "PRP"),
            "skills": task_context.get("skills", []),
        }
        return render_template_file("task_assignment.md.j2", ctx)

    def _build_methodology(self) -> str:
        """Build the methodology XML section with TDD workflow instructions."""
        return (TEMPLATES_DIR / "methodology.md").read_text()

    def _build_review_resolution(self) -> str:
        """Build the review resolution XML section with wontfix/disposition CLI documentation."""
        return (TEMPLATES_DIR / "review_resolution.md").read_text()

    def _build_quality_standards(self) -> str:
        """Build the quality standards XML section with testing anti-patterns."""
        return (TEMPLATES_DIR / "quality_standards.md").read_text()

    def _build_completion_workflow(
        self,
        task_id: int | None,
        target_branch: str | None = None,
        required_reviews: list[str] | None = None,
        title: str = "",
        acceptance_criteria: list | None = None,
    ) -> str:
        """Build completion workflow from completion_workflow.md.j2.

        Pure data assembly — resolves reviews, builds context, renders template.
        The template uses {% include 'review_section.md.j2' %} for review composition.
        """
        task_id_str = str(task_id) if task_id is not None else "<task_id>"
        base_flag = (
            f" --base {target_branch}" if target_branch and target_branch != "master" else ""
        )

        # Resolve effective reviews from config or parameter
        if self._config is not None:
            effective_reviews = list(self._config.required_reviews)
        elif required_reviews is not None:
            effective_reviews = required_reviews
        else:
            effective_reviews = []
        has_reviews = bool(effective_reviews)

        # Build review_types data for review_section.md.j2 (included by template)
        review_types = []
        if has_reviews:
            task_context = {
                "task_id": task_id_str,
                "title": title,
                "acceptance_criteria": acceptance_criteria or [],
            }
            for review_type in effective_reviews:
                config = REVIEW_TYPE_AGENTS.get(review_type)
                if not config:
                    continue
                invocation_template = config.get(
                    "invocation", f'Task(subagent_type="{config["agent"]}")'
                )
                rendered_invocation = render(invocation_template, task_context)
                review_types.append(
                    {
                        "name": review_type,
                        "invocation": rendered_invocation,
                        "instruction": config.get("instruction", ""),
                    }
                )

        prior_findings = []
        review_round = 1

        context = {
            "task_id": task_id_str,
            "target_branch": target_branch,
            "base_flag": base_flag,
            "has_reviews": has_reviews,
            "required_reviews": effective_reviews,
            "review_types": review_types,
            "workflow_steps": get_required_steps(has_reviews),
            "prior_findings": prior_findings,
            "review_round": review_round,
        }
        return render_template_file("completion_workflow.md.j2", context)

    def _build_escalation(self) -> str:
        """Build the escalation protocol XML section with BLOCKED: instructions."""
        return (TEMPLATES_DIR / "escalation.md").read_text()

    def _format_verification_commands(self, criteria: list) -> str:
        """Format verification commands section for AC with commands (Task #2860).

        Args:
            criteria: List of acceptance criteria (dicts or strings).

        Returns:
            Markdown section with commands, or empty string if none have commands.
        """
        # Filter criteria with commands
        criteria_with_commands = [c for c in criteria if isinstance(c, dict) and c.get("command")]

        if not criteria_with_commands:
            return ""

        lines = ["## Acceptance Verification Commands"]
        lines.append("")
        lines.append("These commands will be run to verify your work passes:")
        lines.append("")

        for criterion in criteria_with_commands:
            text = criterion.get("text", "")
            command = criterion.get("command", "")
            lines.append(f"- **{text}**")
            lines.append("  ```")
            lines.append(f"  {command}")
            lines.append("  ```")

        return "\n".join(lines)

    def _build_documentation(self) -> str:
        """Build the documentation guidance XML section."""
        return (TEMPLATES_DIR / "documentation.md").read_text()

    def _is_documentation_required(self, task_context: dict) -> bool:
        """Check if documentation_required is true in task metadata."""
        metadata = task_context.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                return False
        return metadata.get("documentation_required") is True
