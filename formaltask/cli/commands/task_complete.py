"""pm-task-complete command - Complete task with evidence validation.

Return codes:
- 0: Success - task completed
- 1: Blocked (failed/timeout/cancelled/error review status)

Note: Greptile review checking moved to merge time (Task #1836).
The pre-merge-commit hook blocks merging if Greptile score < 3.
"""

import logging
import os
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta

from formaltask.cli.base import CLIError
from formaltask.cli.context import with_db_path
from formaltask.cli.exit_codes import ExitCode
from formaltask.cli.output import OutputFormatter
from formaltask.db.helpers import parse_depends_on
from formaltask.exceptions import TaskNotFoundError
from formaltask.tasks import get_task, get_tasks
from formaltask.tasks.guards import GuardViolation
from formaltask.workers.resume import resume_worker_in_tmux

# Constant for commit lookback period in days
LOOKBACK_DAYS = 30


def setup_parser(subparser):
    """Set up argument parser for task-complete command."""
    subparser.add_argument("task_id", type=int, help="Task ID to complete")
    subparser.add_argument(
        "--db-path",
        default=None,
        help="Database path (default: auto-detect)",
    )
    # Note: --skip-review flag removed (Task #1974) - review enforcement moved to Stop hook
    subparser.add_argument(
        "--no-evidence",
        action="store_true",
        help="Skip evidence guard for audit/doc tasks without code changes",
    )
    subparser.add_argument(
        "--completion-evidence",
        type=str,
        metavar="TEXT",
        help="Evidence that work was already done (Task #1893). Sets completion_evidence field.",
    )
    # Note: --force flag removed (Task #2273) - review gates are now mandatory


@with_db_path
def execute(db_path: str, args) -> int:
    """Execute the task-complete command."""
    formatter = OutputFormatter(args) if getattr(args, "json", False) else None

    # Note: Review enforcement is mandatory (Task #2273 removed --force bypass)

    # Use v2 API for preflight/dry_run modes
    if getattr(args, "preflight", False) or getattr(args, "dry_run", False):
        try:
            result = task_complete_v2(args.task_id, db_path=db_path, args=args)
            if formatter:
                print(formatter.success(result, f"✓ Completed task #{args.task_id}"))
            else:
                print(f"✓ Completed task #{args.task_id}")
            return 0
        except CLIError as e:
            if formatter:
                print(formatter.error(e))
            else:
                print(f"Error: {e.message}", file=sys.stderr)
            return int(e.exit_code)
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            return 1

    try:
        no_evidence = getattr(args, "no_evidence", False)
        completion_evidence = getattr(args, "completion_evidence", None)
        task_complete(
            args.task_id,
            db_path=db_path,
            no_evidence=no_evidence,
            completion_evidence=completion_evidence,
        )
        print(f"✓ Completed task #{args.task_id}")
        return 0
    except GuardViolation as e:
        # Evidence guard failures still raise GuardViolation
        # (Review failures are now handled by Stop hook - Task #1974)
        print(f"\nError: {e.message}", file=sys.stderr)
        return 1
    except CLIError as e:
        print(f"Error: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def task_complete(
    task_id: int,
    db_path: str,
    no_evidence=False,
    completion_evidence: str | None = None,
) -> int:
    """Complete a task with evidence validation.

    Args:
        task_id: Task ID to complete
        db_path: Path to the database
        no_evidence: If True, skip evidence validation (for audit/doc tasks)
        completion_evidence: Evidence text for already-done tasks (Task #1893).
            If provided, sets completion_evidence field and satisfies evidence guard.

    Returns:
        int: 0 on success (raises on failure)

    Raises:
        CLIError: If task not found (NOT_FOUND exit code 64)
        GuardViolation: If task cannot be completed (no evidence, review gates failed, etc.)
    """
    # Get task info - use direct DB queries for github columns (Task #1235)
    task = get_task(db_path, task_id)

    # Task #1585: Return CLIError when task is None
    if task is None:
        raise CLIError(
            f"Task #{task_id} not found. Use 'pm task-list <epic>' to see available tasks.",
            exit_code=ExitCode.NOT_FOUND,
        )

    # review_status state machine removed (Task #2013) - Greptile check at merge time
    # Review gates are mandatory (Task #2273 removed --force bypass)
    return _complete_task(
        task_id,
        db_path,
        no_evidence=no_evidence,
        completion_evidence=completion_evidence,
    )


logger = logging.getLogger(__name__)


def _should_chain() -> bool:
    """Check if chain signal file exists."""
    from pathlib import Path

    chain_file = Path(".task/chain")
    if chain_file.exists():
        try:
            chain_file.unlink()
            return True
        except OSError as e:
            logger.warning("Failed to delete chain file: %s", e)
            return False
    return False


def _should_skip_review_gates(
    task_id: int | None = None,
    db_path: str | None = None,
) -> tuple[bool, str | None]:
    """Check if review gates should be skipped.

    Returns:
        (should_skip, branch_name). skip=True for trusted branches:
        - Default branch (e.g., master, main): human-trusted internal work.
        - Runner-spawned branches (`runner/{team}/{name}`): PR creation
          is deferred to /wrapping-up downstream of task completion,
          UNLESS the task's metadata.required_reviews is non-empty —
          in which case the rules engine fires regardless of branch.
    """
    from formaltask.git.utils import _run_git_command, get_default_branch

    result = _run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
    if not result or result.returncode != 0:
        return False, None

    branch = result.stdout.strip()
    if branch == "HEAD":  # Detached
        return False, branch

    if branch == get_default_branch():
        return True, branch
    if branch.startswith("runner/"):
        if task_id is not None and db_path is not None:
            try:
                from formaltask.core.completion_config import get_effective_config
                if get_effective_config(task_id, db_path).required_reviews:
                    return False, branch
            except (sqlite3.Error, TaskNotFoundError, OSError) as e:
                # Conservative: fall through to default skip on DB error.
                # Programming bugs (ImportError, AttributeError) propagate to the
                # outer "Unexpected error" handler — silent skip would mask real regressions.
                logger.warning(
                    "DB error checking required_reviews for task %d, falling through to skip: %s",
                    task_id,
                    e,
                )
        return True, branch
    return False, branch


def _chain_to_next(db_path: str, task_id: int) -> None:
    """Spawn next tasks that have only the completed task as dependency.

    For tasks with multiple dependencies, we can't safely chain because they
    need code from ALL dependencies merged. Those require manual spawn after
    all dependency PRs are merged.
    """
    from formaltask.tasks.lifecycle import InvalidTransitionError, transition_task_status
    from formaltask.tasks.spawnability import get_spawnable_tasks
    from formaltask.workers.spawner import spawn_worker

    task = get_task(db_path, task_id)
    if task is None:
        print("Chain complete")
        return
    epic_name = task["epic_name"]

    spawnable_ids = set(get_spawnable_tasks(db_path))

    epic_tasks = get_tasks(db_path, epic_name)
    epic_task_ids = {t["id"] for t in epic_tasks}

    candidates = spawnable_ids & epic_task_ids
    if not candidates:
        print("Chain complete")
        return

    spawned = []
    multi_dep_tasks = []

    for candidate_id in sorted(candidates):
        candidate = get_task(db_path, candidate_id)
        if candidate is None:
            continue
        deps = parse_depends_on(candidate.get("depends_on"))

        # Multiple deps - can't chain (needs code from ALL, not yet merged)
        if len(deps) > 1:
            multi_dep_tasks.append(candidate_id)
            continue

        # Single dep on completed task → use its branch; otherwise → master
        base = f"task-{task_id}" if deps == [task_id] else None

        try:
            transition_task_status(db_path, candidate_id, "in_progress")
        except InvalidTransitionError:
            continue  # Another chain claimed it
        try:
            spawn_worker(candidate_id, db_path, skip_fetch=True, chain=True, base_branch=base)
            spawned.append(candidate_id)
        except Exception as e:
            logger.error("Failed to spawn task %d: %s", candidate_id, e)
            print(f"Chain: failed to spawn task #{candidate_id}: {e}")

    if spawned:
        print(f"Chained to task(s): {', '.join(f'#{t}' for t in spawned)}")

    # Notify about multi-dependency tasks that can't be auto-chained
    if multi_dep_tasks:
        print("\nTasks with multiple dependencies (spawn after merging all PRs):")
        for t in multi_dep_tasks:
            print(f"  #{t}")
        print(f"  Run: python3 -m formaltask.cli.pm spawn --epic {epic_name}")

    if not spawned and not multi_dep_tasks:
        print("Chain complete")


def _auto_unblock_reporter(completed_task_id: int, db_path: str) -> None:
    """Auto-resume the reporter task when a blocker task completes.

    If the completed task is a blocker (task_type=blocker) with a source_task_id,
    and the source task is blocked_user, resume its worker in tmux.
    """
    task = get_task(db_path, completed_task_id)
    if task is None:
        return

    metadata = task.get("metadata") or {}
    if metadata.get("task_type") != "blocker":
        return

    source_task_id = metadata.get("source_task_id")
    if not source_task_id:
        return

    source_task = get_task(db_path, source_task_id)
    if source_task is None or source_task["status"] != "blocked_user":
        return

    response_msg = f"Blocker task #{completed_task_id} completed: {task['title']}"
    try:
        resume_worker_in_tmux(source_task_id, response_msg)
        print(f"Auto-resumed task #{source_task_id} (blocker #{completed_task_id} completed)")
    except Exception:
        # Fallback: clear blocked state directly (we have db_path; _clear_blocked_state
        # uses get_db_path() which may not resolve in all contexts)
        from formaltask.db.connection import DatabaseConnection

        try:
            with DatabaseConnection(db_path, exclusive=True) as conn:
                conn.execute(
                    "UPDATE tasks SET status = 'in_progress', blocked_question = NULL "
                    "WHERE id = ? AND status IN ('blocked_user', 'blocked')",
                    (source_task_id,),
                )
        except Exception:
            pass
        print(f"Unblocked task #{source_task_id} but could not auto-resume tmux session.")
        print(f"  Respawn manually: ft work spawn {source_task_id}")


def _complete_task(
    task_id: int,
    db_path: str,
    no_evidence: bool = False,
    completion_evidence: str | None = None,
) -> int:
    """Internal helper to complete a task.

    Args:
        task_id: Task ID
        db_path: Path to the database
        no_evidence: If True, skip evidence guard (for audit/doc tasks)
        completion_evidence: Evidence text for already-done tasks (Task #1893).
            If provided, sets completion_evidence field before evidence guard check.

    Returns:
        0 on success
    """
    from formaltask.cli.commands.commit_scan import commit_scan
    from formaltask.db.connection import DatabaseConnection
    from formaltask.git.utils import get_head_sha
    from formaltask.tasks.guards import TaskGuards
    from formaltask.tasks.lifecycle import transition_task_status

    # Set completion_evidence if provided (Task #1893)
    # This must happen BEFORE the evidence guard check
    if completion_evidence:
        # Warn if local uncommitted changes exist (Task #1893)
        # If agent claims work was "already done" but has local changes, they may have done work
        try:
            repo_path = os.environ.get("GIT_REPO_PATH", ".")
            result = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=repo_path,
            )
            if result.returncode == 0 and result.stdout.strip():
                print(
                    f"⚠️  Warning: Task #{task_id} has uncommitted local changes but using --completion-evidence"
                )
                print(
                    "   If you did work, commit it first. --completion-evidence is for work already done before you started."
                )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass  # Git check failed - silently ignore, warning should not block workflow

        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET completion_evidence = ? WHERE id = ?",
                (completion_evidence, task_id),
            )
            conn.commit()

    # Create guards instance once for all guard checks (Task #1964 refactor)
    guards = TaskGuards(db_path)

    # Auto-scan for commits (skip if no_evidence)
    if not no_evidence:
        repo_path = os.environ.get("GIT_REPO_PATH")
        # Calculate lookback date (LOOKBACK_DAYS ago)
        since_date = (datetime.now(tz=UTC) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
        commit_scan(db_path=db_path, task_id=task_id, since=since_date, repo_path=repo_path)

        # Validate evidence (commits or completion_evidence) exist
        guards.check_evidence_required(task_id)

    # Note: Test guard removed (Task #2288) - test verification delegated to CI

    # Branch detection: skip review gates when on default branch (Task #2401)
    # Note: Documentation check is now part of check_review_gates_v2 (Task #2614)
    # Pass task_id + db_path so runner-branch arm can honor metadata.required_reviews (Task #917)
    skip_review_gates, current_branch = _should_skip_review_gates(task_id, db_path)
    if skip_review_gates:
        print(f"Skipping review gates (on {current_branch} branch)")

    # Review gates are mandatory (Task #2273 removed --force bypass)
    # Skip review gates when on default branch (Task #2401)
    if not skip_review_gates:
        from formaltask.core.completion_check import check_completion

        result = check_completion(task_id, db_path)
        if result is None:
            raise GuardViolation("Task not found", "Run required reviews first")
        if not result.allowed:
            raise GuardViolation(
                result.reason or "Completion blocked", "Run required reviews first"
            )

    # Get HEAD SHA for tracking (Task #1829) - may be None outside git repo
    head_sha = get_head_sha()

    # Prompt for learning before irreversible status transition (Task #2451)
    # Skip prompt in non-interactive contexts (CI, scripts, pipes)
    if sys.stdin.isatty():
        try:
            learning = input("What would help the next worker? (Enter to skip): ").strip()
            if learning:
                if len(learning) > 200:
                    print(f"Learning too long ({len(learning)} chars). Max 200. Skipping.")
                else:
                    with DatabaseConnection(db_path) as conn:
                        conn.execute(
                            """UPDATE tasks SET metadata = json_set(
                                COALESCE(metadata, '{}'),
                                '$.learnings',
                                json_insert(
                                    COALESCE(json_extract(metadata, '$.learnings'), json('[]')),
                                    '$[#]',
                                    ?
                                )
                            ) WHERE id = ?""",
                            (learning, task_id),
                        )
                    print(f"Learning captured: {learning}")
        except (KeyboardInterrupt, EOFError):
            pass  # User cancelled - continue with completion

    # Update task status to completed via state machine (Task #1369)
    transition_task_status(db_path, task_id, "completed", head_commit_sha=head_sha)

    # Auto-resume reporter if this was a blocker task
    _auto_unblock_reporter(task_id, db_path)

    # Show newly-unblocked tasks after completion
    _show_unblocked_tasks_after_completion(task_id, db_path)

    # Chain to next task if signal file exists (Task #2375)
    if _should_chain():
        _chain_to_next(db_path, task_id)

    # Merge reminder for worktree agents (Task: faster merge automation)
    print("")
    print("📋 Next: Create PR and merge to prevent stale branches:")
    print(f"   /issue-pr {task_id} --auto-merge")
    print("   /merge-worktree <branch-name>")

    return 0


def _show_unblocked_tasks_after_completion(completed_task_id: int, db_path: str) -> None:
    """Show tasks that became unblocked after completing a task.

    Args:
        completed_task_id: ID of the task that was just completed
        db_path: Path to the database
    """
    from formaltask.db.connection import DatabaseConnection

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()

        # Get epic name for this task
        cursor.execute("SELECT epic_name FROM tasks WHERE id = ?", (completed_task_id,))
        result = cursor.fetchone()
        if not result:
            return
        epic_name = result[0]

        # Get all completed task IDs in this epic
        cursor.execute(
            "SELECT id FROM tasks WHERE epic_name = ? AND status = 'completed'", (epic_name,)
        )
        completed_ids = {row[0] for row in cursor.fetchall()}

        # Get all open tasks with dependencies
        cursor.execute(
            """SELECT id, title, depends_on FROM tasks
               WHERE epic_name = ? AND status = 'open'
               ORDER BY position""",
            (epic_name,),
        )
        open_tasks = cursor.fetchall()

        # Build newly_ready and still_blocked in one pass
        newly_ready = []
        still_blocked = []
        for task_id, title, depends_on_json in open_tasks:
            depends_on = parse_depends_on(depends_on_json)
            # Skip tasks without dependencies on the completed task
            if not depends_on or completed_task_id not in depends_on:
                continue
            incomplete_deps = [dep_id for dep_id in depends_on if dep_id not in completed_ids]
            if not incomplete_deps:
                # All dependencies satisfied - newly ready
                newly_ready.append((task_id, title))
            else:
                # Some dependencies remaining - still blocked
                still_blocked.append((task_id, title, incomplete_deps))

        if newly_ready:
            print("\n✅ Tasks now ready (unblocked):")
            for task_id, title in newly_ready:
                print(f"   #{task_id}: {title}")

        if still_blocked:
            print("\n⏳ Tasks still blocked:")
            for task_id, title, incomplete_deps in still_blocked:
                print(f"   #{task_id}: {title} (waiting on: {incomplete_deps})")


def task_complete_v2(task_id: int, db_path: str, args) -> dict:
    """Complete a task with OutputFormatter support (v2 API).

    Args:
        task_id: Task ID to complete
        db_path: Path to the database
        args: Parsed CLI arguments with json, stream, preflight, dry_run flags

    Returns:
        dict: Result structure with success, data containing task_id, previous_state, new_state

    Raises:
        CLIError: If task not found (NOT_FOUND)
    """
    # Get task - raises CLIError if not found
    task = get_task(db_path, task_id)
    if not task:
        raise CLIError(
            f"Task #{task_id} not found. Use 'pm task-list <epic>' to see available tasks.",
            exit_code=ExitCode.NOT_FOUND,
        )

    previous_state = task["status"]

    # Preflight: return early with can_proceed status
    if getattr(args, "preflight", False):
        from formaltask.db.connection import DatabaseConnection

        blockers = []
        if previous_state != "in_progress":
            blockers.append(
                {
                    "type": "invalid_state",
                    "message": f"Task is '{previous_state}', must be 'in_progress'",
                }
            )

        # Check for evidence (commits)
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM commits WHERE task_id = ?", (task_id,))
            commit_count = cursor.fetchone()[0]
        if commit_count == 0:
            blockers.append({"type": "no_evidence", "message": "Task has no commits linked"})

        return {"preflight": {"can_proceed": not blockers, "blockers": blockers}}

    # Dry-run: return without executing
    if getattr(args, "dry_run", False):
        if previous_state != "in_progress":
            return {"dry_run": {"would_fail": True, "reason": "invalid_state"}}
        return {
            "dry_run": {
                "side_effects": [
                    {"type": "status_change", "from": previous_state, "to": "completed"}
                ]
            }
        }

    # Validate state before completing
    if previous_state != "in_progress":
        raise CLIError(
            f"Task #{task_id} is in '{previous_state}' state, must be 'in_progress' to complete",
            exit_code=ExitCode.INVALID_STATE,
        )

    # Complete task - convert GuardViolation to CLIError
    try:
        _complete_task(task_id, db_path)
    except GuardViolation as e:
        raise CLIError(
            str(e),
            exit_code=ExitCode.INVALID_STATE,
        ) from e

    return {
        "success": True,
        "data": {
            "task_id": task_id,
            "previous_state": previous_state,
            "new_state": "completed",
        },
    }
