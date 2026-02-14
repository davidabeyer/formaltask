"""Phase: Task Context Injection via #task:NNN trigger.

Task #2569: Plain function architecture (no phase_engine).
Migrated from hooks/user_prompt/task_context_trigger.py per Task #2549.

Injects task context when user prompt contains #task:NNN pattern.
Unlike SessionStart hooks, this only injects context when explicitly triggered.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from formaltask.tasks.context import load_task_context

logger = logging.getLogger(__name__)


def extract_task_id(prompt: str) -> int | None:
    """Extract task ID from #task:NNN pattern in prompt.

    Returns task ID as int if found, None otherwise.
    """
    match = re.search(r"#task:(\d+)", prompt)
    if match:
        return int(match.group(1))
    return None


def format_task_context_simple(task_context: dict) -> str:
    """Format task context as simple markdown for on-demand injection.

    This is a lightweight formatter for #task:NNN triggers that only includes
    task-specific information (title, epic, description, acceptance criteria, PRP).
    It intentionally omits methodology and quality standards sections.

    Args:
        task_context: Dict with id, title, description, epic_name,
            artifact_content, acceptance_criteria fields.

    Returns:
        Markdown-formatted task context string.
    """
    task_id = task_context.get("id", "?")
    title = task_context.get("title", "Unknown Task")
    description = task_context.get("description", "")
    epic_name = task_context.get("epic_name", "")
    artifact_content = task_context.get("artifact_content", "")
    acceptance_criteria = task_context.get("acceptance_criteria", [])

    lines = [f"# Task #{task_id}: {title}"]

    if epic_name:
        lines.append(f"\n**Epic:** {epic_name}")

    if description:
        lines.append(f"\n## Description\n\n{description}")

    # Acceptance criteria from database table
    if acceptance_criteria:
        lines.append("\n## Acceptance Criteria")
        for criterion in acceptance_criteria:
            text = criterion["text"] if isinstance(criterion, dict) else criterion
            lines.append(f"- {text}")

    if artifact_content:
        lines.append(f"\n## PRP\n\n{artifact_content}")

    return "\n".join(lines)


def check(ctx: dict) -> dict | None:
    """Inject task context when prompt contains #task:NNN pattern.

    Args:
        ctx: Context dict with prompt, cwd, session_id fields

    Returns:
        dict with "context" key if task found, None otherwise
    """
    prompt = ctx.get("prompt", "")
    cwd = ctx.get("cwd", "")

    # Check for #task:NNN pattern
    task_id = extract_task_id(prompt)
    if task_id is None:
        return None

    # Load task context from database
    cwd_path = Path(cwd) if cwd else Path.cwd()

    # Check .task/project_root for worktree case
    project_root_file = cwd_path / ".task" / "project_root"
    if project_root_file.exists():
        project_root = Path(project_root_file.read_text().strip())
        db_path = project_root / ".claude" / "formaltask.db"
    else:
        db_path = cwd_path / ".claude" / "formaltask.db"

    task_context = load_task_context(task_id, db_path)
    if task_context is None:
        return None

    # Add task ID to context
    task_context["id"] = task_id
    formatted = format_task_context_simple(task_context)

    return {"context": formatted}
