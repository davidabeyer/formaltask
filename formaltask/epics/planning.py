"""Planning workflow state management using database (Task #2317)."""

import json
from pathlib import Path

from formaltask.db.connection import DatabaseConnection

# Stage definitions: (stage, next_stage, reject_stage, phase)
WORKFLOW = [
    ("plan", "critique", None, "DESIGN"),
    ("critique", "plan-decompose", "revise-plan", "DESIGN"),
    ("revise-plan", "critique", None, "DESIGN"),
    ("plan-decompose", "critique-specs", None, "DECOMPOSE"),
    ("critique-specs", "revise-specs", None, "DECOMPOSE"),
    ("revise-specs", "plan-test-strategy", None, "DECOMPOSE"),
    ("plan-test-strategy", "epic-decompose", None, "IMPLEMENT"),
    ("epic-decompose", None, None, "IMPLEMENT"),
]


STAGES = {s[0]: s for s in WORKFLOW}


def load_state(project: str, db_path: str | Path) -> dict:
    """Load project state from database."""
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT current_stage, loops FROM planning_state WHERE project_name = ?",
            (project,),
        )
        row = cursor.fetchone()
        if row:
            stage = row[0] if row[0] else None  # Empty string -> None
            return {"stage": stage, "loops": json.loads(row[1])}
    return {"stage": None, "loops": {}}


def begin_stage(project: str, stage: str, db_path: str | Path) -> int:
    """Start a planning stage. Returns round number (1-indexed).

    Atomically reads current state, increments stage counter, writes back.
    Call this first thing in every planning skill.
    """
    from datetime import UTC, datetime

    with DatabaseConnection(db_path, exclusive=True) as conn:
        cursor = conn.cursor()

        # Read current loops
        cursor.execute("SELECT loops FROM planning_state WHERE project_name = ?", (project,))
        row = cursor.fetchone()
        loops = json.loads(row[0]) if row else {}

        # Increment this stage's counter
        round_num = loops.get(stage, 0) + 1
        loops[stage] = round_num

        # Write back
        timestamp = datetime.now(UTC).isoformat()
        cursor.execute(
            """INSERT INTO planning_state (project_name, current_stage, last_command, loops, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(project_name) DO UPDATE SET
                   current_stage = excluded.current_stage,
                   last_command = excluded.last_command,
                   loops = excluded.loops,
                   updated_at = excluded.updated_at""",
            (project, stage, f"/{stage} {project}", json.dumps(loops), timestamp),
        )

        return round_num


def get_round(project: str, stage: str, db_path: str | Path) -> int:
    """Get current round number for a stage without incrementing.

    Use this to read the round after begin_stage() has been called (e.g., by hook).
    Returns 1 if no state exists (safe default for testing/direct calls).
    """
    state = load_state(project, db_path)
    return state["loops"].get(stage, 1)
