"""Auto-spawn orchestration — shared logic for watch daemon and dashboard.

Extracted from watch.py to enable reuse. Contains:
- evaluate_orchestration_rules: rule evaluation loop with dedup
- send_notification: macOS osascript notification
- count_running_workers: tmux session count
- auto_spawn_cycle: spawn loop with max_workers cap and error recovery
- spawn_supervisor_if_needed: spawn Claude supervisor for blocked workers
"""

import json
import logging
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from formaltask import tmux
from formaltask.core.rules import Rule, apply_rules
from formaltask.db.connection import DatabaseConnection
from formaltask.tasks.lifecycle import InvalidTransitionError, transition_task_status
from formaltask.tasks.spawnability import get_spawnable_tasks
from formaltask.tmux import get_all_task_sessions
from formaltask.workers.inbox import get_blocked_workers
from formaltask.workers.spawner import SpawnError, spawn_worker

logger = logging.getLogger(__name__)

# Track last fired timestamps per (task_id, rule_name) to prevent duplicate firings
_last_fired: dict[tuple[int, str | None], float] = {}

# Sentinel for DB errors
DB_ERROR = -1


def evaluate_orchestration_rules(db_path: str, rules: list[Rule]) -> None:
    """Evaluate orchestration rules against in-progress and blocked tasks.

    Queries tasks with status IN ('in_progress', 'blocked'), builds context
    for each, evaluates rules, and executes matched actions (notify).
    Uses _last_fired to prevent duplicate firings per (task_id, rule_name).
    """
    import sqlite3

    from formaltask.core.rules import evaluate

    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                """
                SELECT id, status, created_at, metadata
                FROM tasks
                WHERE status IN ('in_progress', 'blocked')
                """
            )
            tasks = cursor.fetchall()
    except sqlite3.OperationalError as e:
        logger.debug("Skipping orchestration rules: %s", e)
        return

    now = time.time()

    for task in tasks:
        task_id = task["id"]
        status = task["status"]
        created_at = task["created_at"]

        try:
            created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            duration = (datetime.now(UTC) - created_dt).total_seconds()
        except (ValueError, TypeError, AttributeError):
            duration = 0

        try:
            metadata = json.loads(task["metadata"] or "{}")
        except json.JSONDecodeError:
            metadata = {}

        context = {
            "task_id": task_id,
            "status": status,
            "duration": duration,
            "metadata": metadata,
        }

        output, target = apply_rules(rules, context)

        if output and target:
            rule_name = None
            for rule in rules:
                if evaluate(rule.when, context):
                    rule_name = rule.name or rule.when
                    break

            dedup_key = (task_id, rule_name)
            if dedup_key in _last_fired:
                continue

            _last_fired[dedup_key] = now

            if target == "notify":
                send_notification(output)


def send_notification(message: str) -> None:
    """Send macOS notification via osascript."""
    escaped = message.replace("\\", "\\\\").replace('"', '\\"')
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                f'display notification "{escaped}" with title "FormalTask"',
            ],
            capture_output=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        logger.warning("Failed to send notification: %s", e)


def count_running_workers() -> int:
    """Count running workers by tmux sessions (source of truth)."""
    try:
        return len(get_all_task_sessions())
    except (OSError, ValueError) as e:
        logger.warning("Failed to count tmux sessions: %s", e)
        return DB_ERROR


def auto_spawn_cycle(
    db_path: str,
    max_workers: int,
    *,
    orchestration_rules: list[Rule] | None = None,
    check_supervisor: bool = False,
) -> list[int]:
    """Run one spawn cycle: rules, spawn, supervisor.

    Returns list of successfully spawned task IDs.
    Respects max_workers cap. Resets task status to 'open' on SpawnError.

    Args:
        orchestration_rules: If provided, evaluate these rules before spawning.
        check_supervisor: If True, spawn supervisor for blocked workers.
    """
    if orchestration_rules:
        evaluate_orchestration_rules(db_path, orchestration_rules)

    running = count_running_workers()
    if running == DB_ERROR:
        return []

    spawnable = get_spawnable_tasks(db_path)
    available_slots = max_workers - running

    if available_slots <= 0 or not spawnable:
        if check_supervisor:
            spawn_supervisor_if_needed(db_path)
        return []

    tasks_to_spawn = spawnable[:available_slots]
    spawned = []

    for task_id in tasks_to_spawn:
        try:
            transition_task_status(db_path, task_id, "in_progress")
        except InvalidTransitionError:
            logger.info("Task %d claimed by another process, skipping", task_id)
            continue

        try:
            spawn_worker(task_id, db_path)
            logger.info("Spawned task-%d", task_id)
            spawned.append(task_id)
        except (SpawnError, ValueError, OSError) as e:
            logger.error("Failed to spawn task %d: %s", task_id, e)
            try:
                transition_task_status(db_path, task_id, "open", force=True)
            except (InvalidTransitionError, OSError) as reset_err:
                logger.error("Failed to reset task %d status: %s", task_id, reset_err)

    if check_supervisor:
        spawn_supervisor_if_needed(db_path)

    return spawned


def spawn_supervisor_if_needed(db_path: str) -> bool:
    """Spawn Claude supervisor if there are blocked workers and no supervisor running.

    Returns True if supervisor was spawned, False otherwise.
    """
    blocked = get_blocked_workers(db_path)
    supervisor_exists = tmux.session_exists("supervisor")

    # Clean up stale supervisor (Claude exited but tmux session alive)
    if supervisor_exists and not tmux.is_pane_alive("supervisor"):
        logger.info("Killing stale supervisor session (pane dead)")
        tmux.kill_session("supervisor")
        supervisor_exists = False

    if not blocked or supervisor_exists:
        return False

    logger.info("Spawning supervisor for %d blocked workers", len(blocked))
    project_root = Path(db_path).parent.parent  # .claude/ -> project root
    if tmux.create_session(
        "supervisor", cwd=str(project_root), env_vars={"SUPERVISOR_UNATTENDED": "1"}
    ):
        tmux.send_keys(
            "supervisor",
            'claude --dangerously-skip-permissions "Run /supervisor skill. Process all blocked workers, then exit when inbox is empty."',
        )
        return True

    logger.warning("Failed to spawn supervisor, will retry next cycle")
    return False
