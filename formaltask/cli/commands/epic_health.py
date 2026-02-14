"""Epic health command - Task #1786."""

from formaltask.cli.context import CLIContext, with_repository
from formaltask.cli.exit_codes import ExitCode
from formaltask.cli.output import OutputFormatter
from formaltask.epics import get_epic
from formaltask.tasks.dependencies import validate_epic_health


def setup_parser(subparser):
    """Configure arguments."""
    subparser.add_argument("epic_name", help="Epic to validate")
    subparser.add_argument("--db-path", default=None, help="Database path")


@with_repository
def execute(ctx: CLIContext, args) -> int:
    """Execute command."""
    formatter = OutputFormatter(args)

    epic = get_epic(ctx.db_path, args.epic_name)
    if not epic:
        print(f"Error: Epic '{args.epic_name}' not found")
        return ExitCode.NOT_FOUND.value

    issues = validate_epic_health(ctx.db_path, args.epic_name)

    if not issues:
        print(
            formatter.success(
                data={"epic_name": args.epic_name, "healthy": True, "issues": []},
                human_template="✓ Epic '{epic_name}' is healthy - no orphaned dependencies found",
            )
        )
        return ExitCode.SUCCESS.value

    # Format issues for output
    formatted_issues = [{"task_id": issue["task_id"], "issue": issue["issue"]} for issue in issues]

    if formatter.json_mode:
        print(
            formatter.success(
                data={"epic_name": args.epic_name, "healthy": False, "issues": formatted_issues},
                human_template="",
            )
        )
    else:
        print(f"⚠ Epic '{args.epic_name}' has {len(issues)} dependency issue(s):\n")
        for issue in issues:
            print(f"  Task #{issue['task_id']}: {issue['issue']}")
            if "cancelled" in issue["issue"].lower():
                print("    → Fix: Update depends_on or cancel this task")
            elif "non-existent" in issue["issue"].lower():
                print("    → Fix: Remove invalid dependency")
            elif "cross-epic" in issue["issue"].lower():
                print("    → Warning: Cross-epic dependency (not blocking)")
            print()
    return ExitCode.GENERAL_ERROR.value
