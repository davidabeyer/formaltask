"""Restart orphaned workers - finds in_progress tasks with dead/missing workers.

antirez-style: one command, one job.
- get_orphaned_workers() finds in_progress tasks with no session OR dead pane
- --resume: try to continue Claude session (keeps context)
- Default: reset to open and spawn fresh

Usage:
    ft work restart              # Spawn fresh (loses context)
    ft work restart --resume     # Resume Claude sessions (keeps context)
    ft work restart --dry-run    # Preview only
"""

import logging

from formaltask.cli.context import with_db_path
from formaltask.paths import task_worktree
from formaltask.tasks.lifecycle import InvalidTransitionError, transition_task_status
from formaltask.workers.crash_detector import get_orphaned_workers
from formaltask.workers.spawner import SpawnError, spawn_worker

logger = logging.getLogger(__name__)

# ANSI colors
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
DIM = "\033[2m"
CYAN = "\033[36m"
NC = "\033[0m"


def setup_parser(subparser):
    """Configure argument parser for restart-dead command."""
    subparser.add_argument("--db-path", default=None, help="Database path")
    subparser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would restart without doing it",
    )
    subparser.add_argument(
        "--resume",
        action="store_true",
        help="Resume Claude sessions with --continue (keeps context)",
    )


def _can_resume(task_id: int) -> bool:
    """Check if task has session_id file for resume."""
    session_id_file = task_worktree(task_id) / ".task" / "session_id"
    return session_id_file.exists()


def _try_resume(task_id: int) -> bool:
    """Try to resume worker with --continue. Returns True on success."""
    from formaltask.workers.resume import (
        WorkerResumeError,
        resume_worker_in_tmux,
    )

    try:
        resume_worker_in_tmux(task_id, response="Resuming after crash/restart")
        return True
    except WorkerResumeError as e:
        logger.debug("Resume failed for task %d: %s", task_id, e)
        return False


@with_db_path
def execute(db_path: str, args) -> int:
    """Find and restart orphaned workers."""
    dry_run = args.dry_run
    use_resume = args.resume

    orphaned = get_orphaned_workers(db_path=db_path)

    if not orphaned:
        print(f"{DIM}No orphaned workers found{NC}")
        return 0

    print(f"{YELLOW}Found {len(orphaned)} orphaned worker(s){NC}")

    if dry_run:
        for task_id in orphaned:
            can_resume = _can_resume(task_id)
            mode = f"{CYAN}resume{NC}" if (use_resume and can_resume) else "spawn"
            print(f"  {DIM}[dry-run]{NC} Would {mode} #{task_id}")
        return 0

    restarted = 0
    resumed = 0

    for task_id in orphaned:
        # Try resume first if --resume flag and session_id exists
        if use_resume and _can_resume(task_id):
            if _try_resume(task_id):
                print(f"  {CYAN}↺{NC} #{task_id} resumed (--continue)")
                logger.info("Resumed orphaned task-%d", task_id)
                resumed += 1
                continue
            # Resume failed, fall through to fresh spawn
            print(f"  {DIM}#{task_id} resume failed, spawning fresh{NC}")

        # Reset to open first (force=True because in_progress->open isn't normally valid)
        try:
            transition_task_status(db_path, task_id, "open", force=True)
        except (InvalidTransitionError, ValueError) as e:
            print(f"  {RED}✗{NC} #{task_id} reset failed: {e}")
            logger.error("Failed to reset task %d: %s", task_id, e)
            continue

        # Now transition to in_progress and spawn
        try:
            transition_task_status(db_path, task_id, "in_progress")
            spawn_worker(task_id, db_path)
            print(f"  {GREEN}↻{NC} #{task_id} restarted")
            logger.info("Restarted orphaned task-%d", task_id)
            restarted += 1
        except (SpawnError, InvalidTransitionError, ValueError, OSError) as e:
            print(f"  {RED}✗{NC} #{task_id} spawn failed: {e}")
            logger.error("Failed to spawn task %d: %s", task_id, e)
            # Reset back to open so it can be retried
            try:
                transition_task_status(db_path, task_id, "open", force=True)
            except (InvalidTransitionError, ValueError):
                pass

    if use_resume:
        print(
            f"{GREEN}Resumed {resumed}, restarted {restarted}/{len(orphaned)} orphaned workers{NC}"
        )
    else:
        print(f"{GREEN}Restarted {restarted}/{len(orphaned)} orphaned workers{NC}")
    return 0
