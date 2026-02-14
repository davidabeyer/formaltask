"""SessionStart hook to load task context for worktree agents."""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import contextlib
import json
import logging
import sys
from pathlib import Path

from formaltask.db.connection import DatabaseConnection
from formaltask.tasks.context import load_task_context as _load_task_context
from formaltask.workers.instructions import WorkerInstructionBuilder


def inject_blocked_context(task_id: int, db_path: Path) -> str:
    """Retrieve blocked question for a resuming worker.

    When a worker resumes after being blocked, this function retrieves
    the pending question that caused the block.

    Task #2388: Blocking state now lives on tasks table (blocked_question column).
    The blocked_summary concept was removed as part of this cleanup.

    Args:
        task_id: The task ID of the resuming worker.
        db_path: Path to the FormalTask database.

    Returns:
        Formatted string with pending question,
        or empty string if no blocked question exists.
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT blocked_question FROM tasks WHERE id = ?",
            (task_id,),
        )
        row = cursor.fetchone()
        if not row or not row[0]:
            return ""
        blocked_question = row[0]
    return f"PENDING QUESTION:\n{blocked_question}"


def load_task_context(task_id: int, db_path: Path) -> dict | None:
    """Load task context from database.

    Returns None if database doesn't exist or task not found.
    Delegates to shared utility which loads acceptance_criteria from DB.
    """
    return _load_task_context(task_id, db_path)


def inject_skills_context(skills: list[str] | None) -> str | None:
    """Format skills loading instructions if skills present.

    Args:
        skills: List of skill names from task metadata, or None.

    Returns:
        Formatted string with skill loading instructions, or None if no skills.
    """
    if not skills:
        return None
    skill_list = ", ".join(f"/{s}" for s in skills)
    return f"""**Skills to load:**
Before starting, load these skills: {skill_list}
(Invoke each with Skill(skill="name"))
"""


def _extract_targeted_text(learning: object, task_id: int) -> str | None:
    """Extract text from targeted learning if task_id is in targets.

    Task #2673: Learnings use {text, targets} format.

    Args:
        learning: Learning object (dict with text/targets) or old format (str).
        task_id: Current task ID to filter by.

    Returns:
        Learning text if targeted to task_id, otherwise None.
    """
    # Skip old format (plain strings)
    if isinstance(learning, str):
        return None
    # Skip non-dict objects
    if not isinstance(learning, dict):
        return None
    # Skip objects missing targets field
    targets = learning.get("targets")
    if not targets or not isinstance(targets, list):
        return None
    # Skip if current task not in targets
    if task_id not in targets:
        return None
    # Extract and return text
    text = learning.get("text", "")
    return text if text else None


def inject_sibling_learnings(task_id: int, epic_name: str, db_path: Path) -> str | None:
    """Query sibling tasks and format learnings targeted at this task.

    Task #2673: Learnings now use {text, targets} format. Only inject learnings
    where current task_id is in the targets array. Plain strings and objects
    without targets are silently skipped.

    Args:
        task_id: Current task ID (to exclude from siblings and filter by target).
        epic_name: Epic name to filter siblings.
        db_path: Path to the FormalTask database.

    Returns:
        Formatted string with targeted sibling learnings, or None if no learnings.
    """
    try:
        with DatabaseConnection(db_path) as conn:
            rows = conn.execute(
                """SELECT id, title, metadata FROM tasks
                   WHERE epic_name = ?
                     AND status = 'completed'
                     AND id != ?
                     AND json_array_length(json_extract(metadata, '$.learnings')) > 0""",
                (epic_name, task_id),
            ).fetchall()
    except Exception as e:
        logging.warning("Failed to query sibling learnings: %s", e)
        return None

    if not rows:
        return None

    lines = ["**Learnings from sibling tasks:**"]
    for row in rows:
        try:
            metadata = json.loads(row["metadata"] or "{}")
            learnings = metadata.get("learnings", [])
            if not isinstance(learnings, list):
                continue
            for learning in learnings:
                text = _extract_targeted_text(learning, task_id)
                if text:
                    lines.append(f'- Task #{row["id"]} ({row["title"]}): "{text}"')
        except json.JSONDecodeError as e:
            logging.warning("Failed to parse learnings from Task #%s: %s", row["id"], e)
            continue

    # Return None if no learnings were successfully parsed
    if len(lines) == 1:
        return None

    return "\n".join(lines)


def format_context(task_context: dict, db_path: Path | None = None) -> str:
    """Format task context as structured prompt for agent injection.

    Delegates to WorkerInstructionBuilder.for_task_start() for all section generation.
    Passes task_id for concrete commands in completion workflow (Task #2240).
    Passes target_branch for PR instructions (Task #2428).
    Task #2821: Passes config from get_effective_config when db_path provided.

    Args:
        task_context: Task context dict with id, title, etc.
        db_path: Optional database path for loading CompletionConfig.
    """
    task_id = task_context.get("id")
    target_branch = task_context.get("target_branch")

    # Task #2821: Load config from db when available
    config = None
    if db_path is not None and task_id is not None:
        from formaltask.core.completion_config import get_effective_config
        from formaltask.exceptions import TaskNotFoundError

        try:
            config = get_effective_config(task_id, db_path)
        except TaskNotFoundError:
            pass  # Task doesn't exist yet, use builder defaults

    builder = WorkerInstructionBuilder(config=config)
    return builder.for_task_start(task_context, task_id=task_id, target_branch=target_branch)


def _resolve_db_path(cwd: Path) -> Path:
    """Resolve database path from worktree configuration.

    Priority: main_repo (has DB) > project_root > cwd
    """
    main_repo_file = cwd / ".task" / "main_repo"
    project_root_file = cwd / ".task" / "project_root"

    if main_repo_file.exists():
        try:
            main_repo = Path(main_repo_file.read_text().strip())
            return main_repo / ".claude" / "formaltask.db"
        except OSError:
            pass
    elif project_root_file.exists():
        try:
            project_root = Path(project_root_file.read_text().strip())
            return project_root / ".claude" / "formaltask.db"
        except OSError:
            pass
    return cwd / ".claude" / "formaltask.db"


def _extract_skills_from_metadata(task_context: dict) -> list[str]:
    """Extract skills list from task metadata."""
    metadata = task_context.get("metadata", {})
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    return metadata.get("skills", [])


def process(data: dict) -> dict:
    """Process hook data and return result.

    This function can be called directly by the dispatcher.

    Args:
        data: Hook input with optional 'cwd' field.

    Returns:
        Hook output dict with additionalContext, or empty dict.
    """
    cwd = Path(data.get("cwd", ".")) if data.get("cwd") else Path.cwd()
    task_id_file = cwd / ".task" / "id"

    # Not a worktree - return empty
    if not task_id_file.exists():
        return {}

    try:
        task_id = int(task_id_file.read_text().strip())
    except (ValueError, OSError):
        return {}

    db_path = _resolve_db_path(cwd)
    task_context = load_task_context(task_id, db_path)

    if not task_context:
        return {}

    task_context["id"] = task_id

    # Task #2428: Read target branch for PR instructions
    target_branch_file = cwd / ".task" / "target_branch"
    if target_branch_file.exists():
        with contextlib.suppress(OSError):
            task_context["target_branch"] = target_branch_file.read_text().strip()

    formatted = format_context(task_context, db_path=db_path)

    # Inject skills context (Task #2355)
    skills = _extract_skills_from_metadata(task_context)
    skills_context = inject_skills_context(skills)
    if skills_context:
        formatted = skills_context + "\n\n" + formatted

    # Inject sibling learnings (Task #2355)
    epic_name = task_context.get("epic_name")
    if epic_name:
        learnings_context = inject_sibling_learnings(task_id, epic_name, db_path)
        if learnings_context:
            formatted = learnings_context + "\n\n" + formatted

    # Inject blocked context for resumed workers (P1-1 fix)
    blocked_context = inject_blocked_context(task_id, db_path)
    if blocked_context:
        formatted = blocked_context + "\n\n" + formatted

    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": formatted}}


def main() -> None:
    """Entry point for SessionStart hook (stdout-based)."""
    result = process({})
    if result:
        print(json.dumps(result))
    else:
        print("{}")


if __name__ == "__main__":
    main()
