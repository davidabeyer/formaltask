"""ft comment — add comments to tasks."""

from formaltask.cli.context import with_db_path
from formaltask.db.connection import DatabaseConnection

COMMAND_NAME = "comment"
COMMAND_HELP = "Add a comment to a task"


def setup_parser(subparser):
    subparser.add_argument("task_id", type=int, help="Task ID to comment on")
    subparser.add_argument("text", help="Comment text")
    subparser.add_argument("--db-path", default=None, help="Database path (default: auto-detect)")


@with_db_path
def execute(db_path: str, args) -> int:
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM tasks WHERE id = ?", (args.task_id,))
        if not cursor.fetchone():
            print(f"Error: Task #{args.task_id} not found")
            return 1

        cursor.execute(
            "INSERT INTO task_comments (task_id, text) VALUES (?, ?)",
            (args.task_id, args.text),
        )
        conn.commit()
        print(f"Added comment to task #{args.task_id}")

    return 0
