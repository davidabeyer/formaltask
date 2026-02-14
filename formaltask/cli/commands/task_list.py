"""pm-task-list command - List tasks for an epic."""

from formaltask.cli.base import CLIError
from formaltask.cli.context import with_db_path
from formaltask.cli.exit_codes import ExitCode
from formaltask.cli.output import OutputFormatter
from formaltask.db.connection import DatabaseConnection
from formaltask.git.github import get_prs_for_tasks


def setup_parser(subparser):
    """Set up argument parser for task-list command."""
    subparser.add_argument("epic_name", help="Epic name")
    subparser.add_argument(
        "--status",
        choices=["open", "in_progress", "completed"],
        help="Filter by status",
    )
    subparser.add_argument(
        "--search",
        "-s",
        help="Filter tasks by title or description (case-insensitive)",
    )
    subparser.add_argument(
        "--db-path",
        default=None,
        help="Database path (default: auto-detect)",
    )


@with_db_path
def execute(db_path: str, args) -> int:
    """Execute the task-list command."""
    formatter = OutputFormatter(args) if getattr(args, "json", False) else None

    try:
        tasks = task_list(
            args.epic_name,
            db_path=db_path,
            status=getattr(args, "status", None),
            search=getattr(args, "search", None),
        )
    except ValueError as e:
        if formatter is not None:
            raise CLIError(str(e), exit_code=ExitCode.NOT_FOUND) from e
        print(f"Error: {e}")
        return 1

    if not tasks:
        if formatter is not None:
            print(
                formatter.success(
                    {"tasks": [], "total": 0, "epic_name": args.epic_name}, "Tasks listed"
                )
            )
            return 0
        print(f"No tasks found for epic '{args.epic_name}'")
        return 0

    # PR lookup is a display concern - do it here
    task_ids = [t["id"] for t in tasks]
    pr_info_map = get_prs_for_tasks(task_ids)

    # Add PR info to task data
    for task in tasks:
        pr_info = pr_info_map.get(task["id"])
        task["github_pr_number"] = pr_info.number if pr_info else None

    if formatter is not None:
        print(
            formatter.success(
                {"tasks": tasks, "total": len(tasks), "epic_name": args.epic_name}, "Tasks listed"
            )
        )
        return 0

    # Human-readable output
    for task in tasks:
        pr_suffix = f" PR#{task['github_pr_number']}" if task["github_pr_number"] else ""
        print(f"{task['id']} {task['title']} {task['status']}{pr_suffix}")
    print(f"\nTotal: {len(tasks)} tasks")
    return 0


def _escape_like(s: str) -> str:
    """Escape SQL LIKE wildcards (%, _) to match literal characters."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def task_list(
    epic_name: str, db_path: str, status: str | None = None, search: str | None = None
) -> list[dict]:
    """List tasks for an epic.

    Args:
        epic_name: Epic to list tasks for
        db_path: Path to the database
        status: Filter by status (open/in_progress/completed)
        search: Filter by title or description (case-insensitive)

    Returns:
        List of task dictionaries with id, title, status, started_at, completed_at

    Raises:
        ValueError: If epic not found
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM epics WHERE name = ?", (epic_name,))
        if not cursor.fetchone():
            raise ValueError(f"Epic '{epic_name}' not found")

        query = """
            SELECT id, title, status, started_at, completed_at
            FROM tasks
            WHERE epic_name = ?
        """
        params: list[str] = [epic_name]

        if status:
            query += " AND status = ?"
            params.append(status)

        if search:
            pattern = f"%{_escape_like(search)}%"
            query += " AND (title LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')"
            params.append(pattern)
            params.append(pattern)

        query += " ORDER BY position, id"
        cursor.execute(query, params)

        return [
            {
                "id": row[0],
                "title": row[1],
                "status": row[2],
                "started_at": row[3],
                "completed_at": row[4],
            }
            for row in cursor.fetchall()
        ]
