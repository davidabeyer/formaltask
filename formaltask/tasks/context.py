"""Shared task context loading utility."""

import json
import logging
import sqlite3
from pathlib import Path

from formaltask.db.connection import DatabaseConnection

logger = logging.getLogger(__name__)


def load_task_context(task_id: int, db_path: Path) -> dict | None:
    """Load task context from database.

    Loads task details, metadata, and acceptance criteria from the database.
    """
    if not db_path.exists():
        return None

    try:
        with DatabaseConnection(str(db_path)) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT title, description, epic_name, metadata, depends_on FROM tasks WHERE id = ?",
                (task_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            # Load acceptance criteria from table (with command for runnable AC)
            cursor.execute(
                "SELECT text, command FROM acceptance_criteria WHERE task_id = ? ORDER BY id",
                (task_id,),
            )
            criteria_rows = cursor.fetchall()
            acceptance_criteria = [
                {"text": row["text"], "command": row["command"]} for row in criteria_rows
            ]

        # Parse metadata JSON
        metadata = {}
        if row["metadata"]:
            try:
                metadata = json.loads(row["metadata"])
            except json.JSONDecodeError as e:
                logger.warning("Corrupted or invalid JSON in task %d metadata: %s", task_id, str(e))

        return {
            "title": row["title"] or "",
            "description": row["description"] or "",
            "epic_name": row["epic_name"] or "",
            "artifact_type": metadata.get("artifact_type", ""),
            "artifact_content": metadata.get("artifact_content", ""),
            "non_goals": metadata.get("non_goals", []),
            "skills": metadata.get("skills", []),
            "depends_on": row["depends_on"] or "[]",
            "acceptance_criteria": acceptance_criteria,
            "metadata": metadata,
        }

    except sqlite3.Error:
        return None
