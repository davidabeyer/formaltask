"""pm-spawn command - Unified task spawning with status tracking.

Task #1270: Consolidate pm-worker-spawn and pm-parallel-start into unified pm-spawn command.
"""

import argparse
import logging
import os
import subprocess
import time
from typing import Any, Literal, overload

from formaltask.cli.context import with_db_path

# Sequential spawn delay to prevent Claude CLI resource contention
# Multiple simultaneous Claude startups can cause MCP server failures and SIGTERM
SPAWN_DELAY_SECONDS = float(os.environ.get("SPAWN_DELAY_SECONDS", "10.0"))


def setup_parser(subparser):
    """Set up argument parser for spawn command.

    Task #2646: Simplified flags per antirez cleanup:
    - Removed --force (merge check is now a warning, not blocker)
    - Removed --chain/--no-chain (chaining is always on)
    - Added --no-worker (absorbs task-start functionality)
    """
    subparser.add_argument(
        "task_ids", nargs="*", type=int, help="Task IDs to spawn (optional if --epic is used)"
    )
    subparser.add_argument(
        "--epic", dest="epic_name", help="Spawn all dependency-ready tasks in the epic"
    )
    subparser.add_argument(
        "--db-path",
        default=None,
        help="Database path (default: auto-detect)",
    )
    subparser.add_argument(
        "--fresh",
        action="store_true",
        default=False,
        help="Delete existing worktree/branch before recreation for clean start",
    )
    subparser.add_argument(
        "--no-worker",
        action="store_true",
        default=False,
        help="Mark task in_progress without spawning tmux session (replaces task-start)",
    )


@with_db_path
def execute(db_path: str, args: argparse.Namespace) -> int:
    """Execute the spawn command.

    Task #2650: Simplified per antirez cleanup - removed --force/--chain/--preflight/--json,
    added --no-worker to absorb task-start functionality.
    """
    task_ids = args.task_ids if args.task_ids else None
    epic_name = args.epic_name if getattr(args, "epic_name", None) else None
    fresh = getattr(args, "fresh", False)
    no_worker = getattr(args, "no_worker", False)

    try:
        result = pm_spawn(
            task_ids=task_ids,
            epic_name=epic_name,
            db_path=db_path,
            fresh=fresh,
            no_worker=no_worker,
        )
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    for item in result["spawned"]:
        if no_worker:
            print(f"Started task #{item['task_id']} (no worker spawned)")
        else:
            print(f"Spawned task #{item['task_id']} (pid {item['pid']})")
    for item in result["blocked"]:
        print(f"Blocked task #{item['task_id']}: {item['reason']}")
    for item in result["failed"]:
        print(f"Failed task #{item['task_id']}: {item['error']}")

    return 0 if result["spawned"] else (1 if result["blocked"] or result["failed"] else 0)


def send_enter_to_sessions(task_ids: list[int], delay: float = 2.0) -> None:
    """Send enter key to spawned tmux sessions after a delay.

    Args:
        task_ids: List of task IDs whose tmux sessions should receive enter key.
        delay: Seconds to wait before sending enter (default 2.0).
    """
    time.sleep(delay)
    for task_id in task_ids:
        subprocess.run(
            ["tmux", "send-keys", "-t", f"task-{task_id}", "Enter"],
            check=False,
            timeout=10,
        )


from formaltask.tasks.guards import GuardViolation, TaskGuards
from formaltask.tasks.lifecycle import transition_task_status
from formaltask.tmux import session_exists as tmux_session_exists
from formaltask.workers.spawner import spawn_worker


# STUB: type overload signature (standard Python typing pattern)
@overload
def pm_spawn(
    task_ids: list[int] | None,
    epic_name: str | None,
    db_path: str | None,
    preflight: Literal[True],
    fresh: bool = ...,
    no_worker: bool = ...,
) -> dict[str, Any]: ...


# STUB: type overload signature (standard Python typing pattern)
@overload
def pm_spawn(
    task_ids: list[int] | None = ...,
    epic_name: str | None = ...,
    db_path: str | None = ...,
    preflight: Literal[False] = ...,
    fresh: bool = ...,
    no_worker: bool = ...,
) -> dict[str, Any]: ...


def pm_spawn(  # noqa: C901
    task_ids: list[int] | None = None,
    epic_name: str | None = None,
    db_path: str | None = None,
    preflight: bool = False,
    fresh: bool = False,
    no_worker: bool = False,
) -> dict[str, Any]:
    """Spawn workers for tasks with proper status tracking.

    Task #2646: Simplified per antirez cleanup:
    - Removed force (merge check is now a warning, not blocker)
    - Removed chain (chaining is always on)
    - Added no_worker to absorb task-start functionality

    Args:
        task_ids: Specific task IDs to spawn (mutually exclusive with epic_name)
        epic_name: Epic name to spawn all ready tasks from
        db_path: Path to the database
        preflight: If True, validate without executing
        fresh: If True, clean up existing worktree/branch before recreation
        no_worker: If True, mark task in_progress without spawning tmux session

    Returns:
        SpawnResult with spawned, failed, blocked lists (or PreflightResponse if preflight=True)

    Raises:
        ValueError: If both task_ids and epic_name are provided
    """
    if preflight:
        import json as json_module

        blockers = []
        warnings = []

        # Mutual exclusion validation
        if task_ids and epic_name:
            blockers.append("task_ids and epic_name are mutually exclusive")
            return {"preflight": {"can_proceed": False, "blockers": blockers, "warnings": warnings}}

        # Empty task list is always valid
        if task_ids is None:
            task_ids = []
        if not task_ids and not epic_name:
            return {"preflight": {"can_proceed": True, "blockers": [], "warnings": []}}

        # db_path required for epic_name or non-empty task processing
        if (task_ids or epic_name) and db_path is None:
            blockers.append("db_path is required")
            return {"preflight": {"can_proceed": False, "blockers": blockers, "warnings": warnings}}

        # Check task dependencies
        if task_ids and db_path is not None:
            from formaltask.tasks import get_task

            guards = TaskGuards(db_path)
            for task_id in task_ids:
                try:
                    guards.check_dependencies_satisfied(task_id)
                except GuardViolation as e:
                    blockers.append(str(e))

            # Check for missing PRPs (warning, not blocking)
            for task_id in task_ids:
                task = get_task(db_path, task_id)
                has_prp = False
                if task and task.get("metadata"):
                    try:
                        meta = json_module.loads(task["metadata"])
                        if meta.get("artifact_content"):
                            has_prp = True
                    except (json_module.JSONDecodeError, TypeError):
                        pass
                if not has_prp:
                    warnings.append(
                        f"Task #{task_id} has no PRP - context injection will be limited"
                    )

        if blockers:
            return {"preflight": {"can_proceed": False, "blockers": blockers, "warnings": warnings}}
        return {"preflight": {"can_proceed": True, "blockers": [], "warnings": warnings}}

    # Mutual exclusion validation
    if task_ids and epic_name:
        raise ValueError("task_ids and epic_name are mutually exclusive")

    # Handle epic_name - requires db_path
    if epic_name:
        if db_path is None:
            raise ValueError("db_path is required when using epic_name")
        from formaltask.tasks.dependencies import get_ready_tasks

        task_ids = get_ready_tasks(db_path, epic_name)

    if task_ids is None:
        task_ids = []

    results: dict[str, list] = {"spawned": [], "failed": [], "blocked": []}

    # Early return for empty task_ids (before TaskGuards instantiation)
    if not task_ids:
        return results

    # db_path required for non-empty task processing
    if db_path is None:
        raise ValueError("db_path is required")

    guards = TaskGuards(db_path)

    # Task #1850: Batch fetch optimization - fetch once before spawning all workers
    # Worktrees share the same .git directory, so one fetch updates refs for all
    # P2 fix: Get repo root to ensure fetch runs in correct directory
    try:
        repo_root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        repo_root = None  # Fall back to cwd

    try:
        result = subprocess.run(
            ["git", "fetch", "origin", "master"],
            check=False,  # Don't fail spawn if fetch fails (network issues, etc.)
            capture_output=True,
            timeout=30,
            cwd=repo_root,  # P2 fix: Explicit cwd prevents wrong-repo fetch
        )
        # P2 fix: Log fetch failures for debugging stale refs
        if result.returncode != 0:
            stderr = result.stderr.decode() if result.stderr else ""
            logging.getLogger(__name__).debug(
                "Batch fetch failed (returncode=%d): %s - workers will use existing refs",
                result.returncode,
                stderr.strip() or "(no stderr)",
            )
    except subprocess.TimeoutExpired:
        # Network timeout should not block spawning - workers will use existing refs
        logging.getLogger(__name__).warning(
            "Batch fetch timed out after 30s - workers will use existing origin/master refs"
        )

    spawned_count = 0
    for task_id in task_ids:
        try:
            guards.check_dependencies_satisfied(task_id)
            # Task #2646: Merge check is now a warning, not blocker (antirez cleanup)
            merge_warnings = guards.warn_if_dependency_code_missing(task_id)
            for w in merge_warnings:
                print(f"⚠️ {w}")

            # Task #2646: no_worker mode - mark in_progress without spawning tmux
            if no_worker:
                transition_task_status(db_path, task_id, "in_progress", idempotent=True)
                results["spawned"].append({"task_id": task_id, "pid": 0})
                continue

            # Task #2622: Inline tmux check - block active workers unless --fresh
            session_name = f"task-{task_id}"
            if tmux_session_exists(session_name) and not fresh:
                results["blocked"].append(
                    {
                        "task_id": task_id,
                        "reason": f"Worker running. Use --fresh to restart, or: tmux attach -t {session_name}",
                    }
                )
                continue

            # Sequential delay after first spawn to prevent Claude CLI resource contention
            if spawned_count > 0 and SPAWN_DELAY_SECONDS > 0:
                time.sleep(SPAWN_DELAY_SECONDS)

            transition_task_status(db_path, task_id, "in_progress", idempotent=True)
            # Task #2646: chain is always True (antirez cleanup - removed --chain flag)
            pid = spawn_worker(task_id, db_path, skip_fetch=True, fresh=fresh, chain=True)
            results["spawned"].append({"task_id": task_id, "pid": pid})
            spawned_count += 1
        except GuardViolation as e:
            results["blocked"].append({"task_id": task_id, "reason": str(e)})
        except Exception as e:
            results["failed"].append({"task_id": task_id, "error": str(e)})

    # Send Enter to confirm trust prompt after Claude loads (~10s startup time)
    if results["spawned"]:
        spawned_ids = [item["task_id"] for item in results["spawned"]]
        send_enter_to_sessions(spawned_ids, delay=10.0)

    return results
