"""skill-init command - Initialize skill run with DB registration.

Consolidates common skill initialization:
1. Parse project name from argument or path
2. Register in planning_state via begin_stage()
3. Create SkillRun with output directories
4. Output JSON for skill to parse
"""

import argparse
import json
from pathlib import Path

from formaltask.cli.context import with_db_path

COMMAND_NAME = "skill-init"
COMMAND_HELP = "Initialize skill run with DB registration and output directories"


def setup_parser(subparser: argparse.ArgumentParser) -> None:
    """Configure the argument parser for this command."""
    subparser.add_argument(
        "stage",
        help="Stage name (e.g., critique-specs, plan-decompose)",
    )
    subparser.add_argument(
        "project",
        nargs="?",
        default=None,
        help="Project name or path (optional, auto-detects if omitted)",
    )
    subparser.add_argument(
        "--skill",
        default=None,
        help="Skill name for SkillRun (defaults to stage name)",
    )
    subparser.add_argument(
        "--title",
        default=None,
        help="Title for SkillRun (defaults to '{skill} {project} Round {N}')",
    )
    subparser.add_argument(
        "--db-path",
        default=None,
        help="Path to database (default: auto-detect)",
    )


def _extract_project_name(project_arg: str | None) -> str:
    """Extract project name from argument.

    Handles:
    - None -> detect from environment/cwd
    - "my-project" -> "my-project"
    - "/path/to/my-project-plan-v2.md" -> "my-project"
    - "~/projects/my-project/plans/foo.md" -> "my-project"
    """
    if not project_arg:
        # Try environment detection
        from formaltask.utils.skill_output import _detect_project

        detected = _detect_project()
        if detected:
            return detected
        raise ValueError("Could not detect project. Provide project name or path.")

    # Normalize the argument
    project_arg = project_arg.strip()

    # If it looks like a path
    if "/" in project_arg or project_arg.startswith("~"):
        path = Path(project_arg).expanduser().resolve()

        # If it's a file, extract project from filename or parent
        if path.suffix == ".md":
            # Try extracting from plan filename: my-project-plan-v2.md -> my-project
            stem = path.stem
            for suffix in ["-plan", "-spec", "-epic"]:
                if suffix in stem:
                    name = stem.split(suffix)[0]
                    # Strip version suffix: my-project-v2 -> my-project
                    if "-v" in name:
                        name = name.rsplit("-v", 1)[0]
                    return name.lower().replace("_", "-").replace(" ", "-")

            # Check if in ~/projects/{project}/
            home = Path.home()
            projects_dir = home / "projects"
            try:
                rel = path.relative_to(projects_dir)
                parts = rel.parts
                if parts:
                    return parts[0]
            except ValueError:
                pass

            # Fall back to parent directory name
            return path.parent.name.lower().replace("_", "-").replace(" ", "-")
        # It's a directory - use its name
        return path.name.lower().replace("_", "-").replace(" ", "-")

    # Plain project name
    return project_arg.lower().replace("_", "-").replace(" ", "-")


@with_db_path
def execute(db_path: str, args: argparse.Namespace) -> int:
    """Execute the skill-init command.

    Returns:
        0 on success, 1 on failure
    """
    from formaltask.epics.planning import begin_stage
    from formaltask.utils.skill_output import SkillRun

    try:
        project_name = _extract_project_name(args.project)
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        return 1

    stage = args.stage
    skill = args.skill or stage
    # db_path already resolved by @with_db_path decorator

    # Register in DB and get round number
    try:
        current_round = begin_stage(project_name, stage, db_path)
    except Exception as e:
        print(json.dumps({"error": f"begin_stage failed: {e}"}))
        return 1

    # Create SkillRun
    title = args.title or f"{skill} {project_name} Round {current_round}"
    try:
        run = SkillRun.create(skill, title)
    except Exception as e:
        print(json.dumps({"error": f"SkillRun.create failed: {e}"}))
        return 1

    # Output JSON
    result = {
        "project": project_name,
        "stage": stage,
        "round": current_round,
        "skill": skill,
        "title": title,
        "run_dir": str(run.dir),
        "outputs": str(run.outputs),
        "handoffs": str(run.handoffs),
        "reports": str(run.reports_dir),
        "context": str(run.context),
    }

    print(json.dumps(result, indent=2))
    return 0
