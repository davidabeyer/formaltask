"""Skill initialization utilities.

Simple API for skills to initialize with database registration and output directories.

Usage in skills:
    ```python
    from formaltask.skills import skill_init

    init = skill_init("critique-specs", "$ARGUMENTS")
    print(f"Round {init['round']}")

    # Available keys:
    # - project: str
    # - stage: str
    # - round: int
    # - skill: str
    # - title: str
    # - run_dir: Path
    # - outputs: Path
    # - handoffs: Path
    # - reports: Path
    # - context: Path
    # - run: SkillRun (the actual object)
    ```
"""

from pathlib import Path

from formaltask.db.path import get_db_path
from formaltask.epics.planning import get_round
from formaltask.utils.skill_output import SkillRun


def _extract_project_name(project_arg: str | None) -> str:
    """Extract project name from argument.

    Handles:
    - None -> detect from environment/cwd
    - "my-project" -> "my-project"
    - "/path/to/my-project-plan-v2.md" -> "my-project"
    - "~/projects/my-project/plans/foo.md" -> "my-project"
    """
    if not project_arg:
        from formaltask.utils.skill_output import _detect_project

        detected = _detect_project()
        if detected:
            return detected
        raise ValueError("Could not detect project. Provide project name or path.")

    project_arg = project_arg.strip()

    if "/" in project_arg or project_arg.startswith("~"):
        path = Path(project_arg).expanduser().resolve()

        if path.suffix == ".md":
            stem = path.stem
            for suffix in ["-plan", "-spec", "-epic"]:
                if suffix in stem:
                    name = stem.split(suffix)[0]
                    if "-v" in name:
                        name = name.rsplit("-v", 1)[0]
                    return name.lower().replace("_", "-").replace(" ", "-")

            home = Path.home()
            projects_dir = home / "projects"
            try:
                rel = path.relative_to(projects_dir)
                parts = rel.parts
                if parts:
                    return parts[0]
            except ValueError:
                pass

            return path.parent.name.lower().replace("_", "-").replace(" ", "-")
        return path.name.lower().replace("_", "-").replace(" ", "-")

    return project_arg.lower().replace("_", "-").replace(" ", "-")


def skill_init(
    stage: str,
    project_arg: str | None = None,
    *,
    skill: str | None = None,
    title: str | None = None,
    db_path: str | None = None,
) -> dict:
    """Initialize a skill run with database registration.

    Args:
        stage: Stage name (e.g., "critique-specs", "plan-decompose")
        project_arg: Project name or path (auto-detects if None)
        skill: Skill name for SkillRun (defaults to stage)
        title: Title for SkillRun (defaults to "{skill} {project} Round {N}")
        db_path: Database path (auto-detects if None)

    Returns:
        Dict with:
        - project: str
        - stage: str
        - round: int
        - skill: str
        - title: str
        - run_dir: Path
        - outputs: Path
        - handoffs: Path
        - reports: Path
        - context: Path
        - run: SkillRun

    Raises:
        ValueError: If project cannot be detected
    """
    project_name = _extract_project_name(project_arg)
    skill_name = skill or stage
    db = db_path or get_db_path()

    current_round = get_round(project_name, stage, db)

    run_title = title or f"{skill_name} {project_name} Round {current_round}"
    run = SkillRun.create(skill_name, run_title)

    return {
        "project": project_name,
        "stage": stage,
        "round": current_round,
        "skill": skill_name,
        "title": run_title,
        "run_dir": run.dir,
        "outputs": run.outputs,
        "handoffs": run.handoffs,
        "reports": run.reports_dir,
        "context": run.context,
        "run": run,
    }
