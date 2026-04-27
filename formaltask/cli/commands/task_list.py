"""pm-task-list command - List tasks for an epic."""

from formaltask.cli.base import CLIError
from formaltask.cli.context import with_db_path
from formaltask.cli.exit_codes import ExitCode
from formaltask.cli.output import OutputFormatter
from formaltask.db.connection import DatabaseConnection
from formaltask.git.github import get_prs_for_tasks


def setup_parser(subparser):
    """Set up argument parser for task-list command."""
    subparser.add_argument("epic_name", nargs="?", default=None, help="Epic name")
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
        "--all-epics",
        action="store_true",
        dest="all_epics",
        help="Search across all epics (requires --search)",
    )
    subparser.add_argument(
        "--label",
        action="append",
        dest="labels",
        help="Filter by label in metadata (multiple --label for AND)",
    )
    subparser.add_argument(
        "--completed-today",
        action="store_true",
        dest="completed_today",
        help="Show tasks completed today",
    )
    subparser.add_argument(
        "--overdue",
        action="store_true",
        dest="overdue",
        help="Show open tasks with due_date on or before today (local date)",
    )
    subparser.add_argument(
        "--due-before",
        dest="due_before",
        help="Show open tasks with due_date <= YYYY-MM-DD (inclusive)",
    )
    subparser.add_argument(
        "--priority",
        type=int,
        dest="priority",
        help="Filter by priority level (1=highest)",
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
    all_epics = getattr(args, "all_epics", False)
    completed_today = getattr(args, "completed_today", False)
    overdue = getattr(args, "overdue", False)
    due_before = getattr(args, "due_before", None)
    labels = getattr(args, "labels", None)
    priority = getattr(args, "priority", None)
    epic_name = getattr(args, "epic_name", None)

    if due_before and not _is_iso_date(due_before):
        print(f"Error: --due-before expects YYYY-MM-DD, got: {due_before}")
        return 1

    # Validate: epic_name required unless a cross-epic filter flag is used
    if (
        not epic_name
        and not all_epics
        and not completed_today
        and not overdue
        and not due_before
    ):
        print(
            "Error: epic_name required unless --all-epics, --completed-today, "
            "--overdue, or --due-before is used"
        )
        return 1

    try:
        tasks = task_list(
            epic_name,
            db_path=db_path,
            status=getattr(args, "status", None),
            search=getattr(args, "search", None),
            all_epics=all_epics,
            labels=labels,
            completed_today=completed_today,
            overdue=overdue,
            due_before=due_before,
            priority=priority,
        )
    except ValueError as e:
        if formatter is not None:
            raise CLIError(str(e), exit_code=ExitCode.NOT_FOUND) from e
        print(f"Error: {e}")
        return 1

    display_name = epic_name or "(all epics)"

    if not tasks:
        if formatter is not None:
            print(
                formatter.success(
                    {"tasks": [], "total": 0, "epic_name": display_name}, "Tasks listed"
                )
            )
            return 0
        print(f"No tasks found for {display_name}")
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
                {"tasks": tasks, "total": len(tasks), "epic_name": display_name}, "Tasks listed"
            )
        )
        return 0

    # Human-readable output
    for task in tasks:
        pr_suffix = f" PR#{task['github_pr_number']}" if task["github_pr_number"] else ""
        due_suffix = f" (due {task['due_date']})" if task.get("due_date") else ""
        print(f"{task['id']} {task['title']} {task['status']}{pr_suffix}{due_suffix}")
    print(f"\nTotal: {len(tasks)} tasks")
    return 0


def _escape_like(s: str) -> str:
    """Escape SQL LIKE wildcards (%, _) to match literal characters."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _is_iso_date(s: str) -> bool:
    """True if s is a YYYY-MM-DD string that represents a real calendar date."""
    import datetime as _dt

    try:
        _dt.date.fromisoformat(s)
    except (ValueError, TypeError):
        return False
    return True


def task_list(
    epic_name: str | None,
    db_path: str,
    status: str | None = None,
    search: str | None = None,
    all_epics: bool = False,
    labels: list[str] | None = None,
    completed_today: bool = False,
    overdue: bool = False,
    due_before: str | None = None,
    priority: int | None = None,
) -> list[dict]:
    """List tasks, optionally across all epics.

    Args:
        epic_name: Epic to list tasks for (None when all_epics or completed_today)
        db_path: Path to the database
        status: Filter by status (open/in_progress/completed)
        search: Filter by title or description (case-insensitive)
        all_epics: Search across all epics
        labels: Filter by labels in metadata JSON (AND logic)
        completed_today: Show tasks completed since midnight
        overdue: Show open tasks with due_date on or before today (local date)
        due_before: Show open tasks with due_date <= YYYY-MM-DD (inclusive)
        priority: Filter by priority level (1=highest)

    Returns:
        List of task dictionaries with id, title, status, started_at, completed_at, due_date
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()

        if not all_epics and not completed_today and not overdue and not due_before and epic_name:
            cursor.execute("SELECT name FROM epics WHERE name = ?", (epic_name,))
            if not cursor.fetchone():
                raise ValueError(f"Epic '{epic_name}' not found")

        query = (
            "SELECT id, title, status, started_at, completed_at, due_date "
            "FROM tasks WHERE 1=1"
        )
        params: list = []

        if epic_name and not all_epics:
            query += " AND epic_name = ?"
            params.append(epic_name)

        if status:
            query += " AND status = ?"
            params.append(status)

        if search:
            pattern = f"%{_escape_like(search)}%"
            query += " AND (title LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')"
            params.append(pattern)
            params.append(pattern)

        if completed_today:
            query += " AND status = 'completed' AND completed_at >= date('now', 'start of day')"

        if overdue:
            query += " AND status = 'open' AND due_date IS NOT NULL AND due_date <= date('now', 'localtime')"

        if due_before:
            query += " AND status = 'open' AND due_date IS NOT NULL AND due_date <= ?"
            params.append(due_before)

        if priority is not None:
            query += " AND priority = ?"
            params.append(priority)

        if labels:
            for label in labels:
                query += " AND EXISTS (SELECT 1 FROM json_each(json_extract(metadata, '$.labels')) WHERE value = ?)"
                params.append(label)

        query += " ORDER BY position, id"
        cursor.execute(query, params)

        return [
            {
                "id": row[0],
                "title": row[1],
                "status": row[2],
                "started_at": row[3],
                "completed_at": row[4],
                "due_date": row[5],
            }
            for row in cursor.fetchall()
        ]
