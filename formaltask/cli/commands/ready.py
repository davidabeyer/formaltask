"""ft ready — show tasks ready to work on."""

import argparse
import json

COMMAND_NAME = "ready"
COMMAND_HELP = "Show tasks ready to work on (no unmet dependencies)"


def setup_parser(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output as JSON array",
    )
    subparser.add_argument(
        "--db-path",
        "--db",
        default=None,
        help="Database path (default: auto-detect)",
    )


def execute(args: argparse.Namespace) -> int:
    import sqlite3

    from formaltask.db.connection import DatabaseConnection
    from formaltask.db.path import get_db_path

    db_path = args.db_path
    if not db_path:
        try:
            db_path = str(get_db_path())
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}")
            return 1

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT task_id, epic_name, title FROM task_ready_status ORDER BY task_id"
            )
        except sqlite3.OperationalError as e:
            print(f"Error querying task_ready_status view: {e}")
            return 1

        rows = cursor.fetchall()

    if getattr(args, "json_output", False):
        data = [
            {"id": row[0], "epic": row[1], "title": row[2]}
            for row in rows
        ]
        print(json.dumps(data, indent=2))
    else:
        if not rows:
            print("No tasks ready.")
        else:
            print(f"{'ID':>5}  {'Epic':<20}  Title")
            print(f"{'─'*5}  {'─'*20}  {'─'*40}")
            for task_id, epic_name, title in rows:
                print(f"{task_id:>5}  {epic_name:<20}  {title}")

    return 0
