"""pm-task-show command - Show task details."""

import argparse

from formaltask.cli.context import with_db_path
from formaltask.utils.formatting import format_task_label


def setup_parser(subparser: argparse.ArgumentParser) -> None:
    """Configure the argument parser for this command."""
    subparser.add_argument("task_id", type=int, help="Task ID to show")
    subparser.add_argument("--deps", action="store_true", help="Show dependency tree")
    subparser.add_argument("--db-path", default=None, help="Path to database")


def task_show(task_id: int, db_path: str, show_deps: bool = False) -> dict:
    """Show task details. With show_deps=True, includes dependencies/dependents."""
    from formaltask.db.connection import DatabaseConnection
    from formaltask.db.helpers import parse_depends_on

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, status, epic_name, depends_on, is_parallel FROM tasks WHERE id = ?",
            (task_id,),
        )
        row = cursor.fetchone()
        if not row:
            return {}

        result = {"task_id": row[0], "title": row[1], "status": row[2]}
        if not show_deps:
            return result

        depends_on = parse_depends_on(row[4])
        result.update({"epic_name": row[3], "is_parallel": bool(row[5]), "depends_on": depends_on})

        if depends_on:
            placeholders = ",".join("?" * len(depends_on))
            # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
            cursor.execute(
                f"SELECT id, title, status FROM tasks WHERE id IN ({placeholders})", depends_on
            )
            result["dependencies"] = [
                {"id": r[0], "title": r[1], "status": r[2]} for r in cursor.fetchall()
            ]
        else:
            result["dependencies"] = []

        cursor.execute(
            "SELECT id, title, status, depends_on FROM tasks WHERE depends_on LIKE ?",
            (f"%{task_id}%",),
        )
        result["dependents"] = [
            {"id": r[0], "title": r[1], "status": r[2]}
            for r in cursor.fetchall()
            if task_id in parse_depends_on(r[3])
        ]
        return result


@with_db_path
def execute(db_path: str, args: argparse.Namespace) -> int:
    """Execute the task-show command. Returns 0 on success, 1 if not found."""
    result = task_show(args.task_id, db_path, show_deps=args.deps)
    if not result:
        print(f"Task #{args.task_id} not found")
        return 1

    print(f"Task {format_task_label(result['task_id'], result['title'], max_title_length=200)}")
    print(f"Status: {result['status']}")

    if args.deps:
        print(f"Epic: {result['epic_name']}")
        print(f"Parallel: {result['is_parallel']}")
        deps = result["dependencies"]
        print("Depends on:" if deps else "Depends on: (none)")
        for dep in deps:
            print(f"  #{dep['id']} [{dep['status']}] {dep['title']}")
        dependents = result["dependents"]
        print("Dependents:" if dependents else "Dependents: (none)")
        for dep in dependents:
            print(f"  #{dep['id']} [{dep['status']}] {dep['title']}")
    return 0
