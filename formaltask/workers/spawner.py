"""Worker spawning utilities for FormalTask.

Provides spawn_worker() for creating cmux-backed worker sessions.
Used by pm_spawn.py for the `pm spawn` command.

Task #2653: Removed workers table registration (dead code - staleness from transcript mtime)
Note: Moved from formaltask/cli/commands/parallel_start.py (Task #2646)
"""

import contextlib
import logging
import os
import re
import shlex
import subprocess
import time
import uuid
from pathlib import Path

from formaltask import cmux
from formaltask.paths import get_claude_home
from formaltask.state.session import set_current_task
from formaltask.workers.resume import read_and_validate_session_id, verify_session_exists

logger = logging.getLogger(__name__)

__all__ = [
    "SpawnError",
    "validate_task_id",
    "cleanup_existing_worker",
    "spawn_tmux_session",
    "rebase_worktree_onto_target",
    "spawn_worker",
]

# Maximum spawn retry attempts (Task #2275)
MAX_SPAWN_RETRIES = 3

# Worktree base directory
WORKTREE_BASE = get_claude_home() / "worktrees"


def _get_git_dir(worktree_path: str) -> Path | None:
    """Resolve actual .git directory for a path.

    In worktrees, .git is a file containing 'gitdir: /path/to/actual/git/dir'.
    In normal repos, .git is a directory.

    Returns None if neither exists.
    """
    git_path = Path(worktree_path) / ".git"
    if not git_path.exists():
        return None
    if git_path.is_dir():
        return git_path
    # Worktree: .git is a file with 'gitdir: /path'
    try:
        content = git_path.read_text().strip()
        if content.startswith("gitdir: "):
            return Path(content[8:])
    except OSError:
        pass
    return None


# Stale lock threshold: 5 minutes (crash recovery, not race prevention)
STALE_LOCK_SECONDS = 300


def _cleanup_stale_git_locks(worktree_path: str) -> None:
    """Remove stale git lock files that block operations.

    Git leaves index.lock behind when processes crash.
    Only removes locks older than STALE_LOCK_SECONDS to avoid races.
    """
    git_dir = _get_git_dir(worktree_path)
    if not git_dir:
        return

    lock_file = git_dir / "index.lock"
    try:
        mtime = lock_file.stat().st_mtime
        age = time.time() - mtime
        if age > STALE_LOCK_SECONDS:
            lock_file.unlink(missing_ok=True)
            logger.info("Removed stale index.lock (%.0fs old) in %s", age, worktree_path)
    except FileNotFoundError:
        pass  # No lock file - nothing to do


def _get_main_repo_path() -> str:
    """Get the repository root path for PROJECT_ROOT.

    Task #2586: Workers need PROJECT_ROOT to find database.

    Note: git rev-parse --show-toplevel returns the current worktree's root,
    not the main repo. This is fine for PROJECT_ROOT since workers run from
    their worktree and the path is used for .task/ binding resolution.

    Returns:
        Path to git repository root, or current directory if detection fails.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return str(Path.cwd())


from formaltask.db.connection import DatabaseConnection
from formaltask.git import utils as git_utils
from formaltask.git.worktree import cleanup_stale_worktrees


class SpawnError(Exception):
    """Raised when worker spawn fails.

    Task #1419: Custom exception for spawn failures with cleanup context.
    """


def _check_resumable_session(task_id: int, worktree_path: Path) -> str | None:
    """Check if a previous Claude session can be resumed for this task.

    Returns session_id if resumable, None otherwise. Never raises.
    """
    try:
        session_id_file = worktree_path / ".task" / "session_id"
        session_id = read_and_validate_session_id(session_id_file)
        verify_session_exists(session_id, task_id, worktree_path)
        return session_id
    except Exception:
        return None


def validate_task_id(task_id):
    """Validate task_id to prevent path traversal and shell injection attacks."""
    task_id_str = str(task_id)
    if ".." in task_id_str:
        raise ValueError(f"Path traversal detected in task_id: {task_id_str}")
    if not re.match(r"^[a-zA-Z0-9_-]+$", task_id_str):
        raise ValueError(f"Invalid task_id contains illegal characters: {task_id_str}")


def cleanup_existing_worker(task_id: int) -> None:
    """Clean up existing worker resources before fresh spawn."""
    worktree_path = WORKTREE_BASE / f"task-{task_id}"

    if worktree_path.exists():
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
            timeout=30,
        )
        # P2 fix: Check return code to prevent data loss if git status fails
        if result.returncode != 0:
            raise ValueError(
                f"git status failed for task-{task_id} (exit {result.returncode}): {result.stderr}"
            )
        if result.stdout.strip():
            raise ValueError(f"Worktree task-{task_id} has uncommitted changes:\n{result.stdout}")

    session_name = f"task-{task_id}"
    cmux.kill_session(session_name)

    # Step 2: Remove worktree with force flag
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(worktree_path)],
        capture_output=True,
        check=False,
        timeout=30,
    )

    # Step 3: Force-delete local branch
    branch_name = f"task-{task_id}"
    subprocess.run(
        ["git", "branch", "-D", branch_name],
        capture_output=True,
        check=False,
        timeout=10,
    )

    # Task #2653: Worker record deletion removed (workers table deleted)


def _cleanup_failed_spawn_worktree(worktree_path: str, task_id: int) -> None:
    if not Path(worktree_path).exists():
        return

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.stdout.strip():
            logger.warning(
                f"Worktree task-{task_id} has uncommitted changes that will be lost: "
                f"{result.stdout[:200]}"
            )
    except Exception as status_err:
        logger.debug("git status check failed during cleanup: %s", status_err)

    with contextlib.suppress(Exception):
        subprocess.run(
            ["git", "worktree", "remove", "--force", worktree_path],
            capture_output=True,
            timeout=30,
        )


def spawn_tmux_session(
    task_id: int,
    worktree_path: str,
    session_id: str,
    project_root: str | None = None,
    resume: bool = False,
) -> int:
    """Spawn cmux workspace with Claude Code.

    Cleans up on failure: closes workspace, removes worktree.

    Args:
        task_id: Task ID for session naming and logging.
        worktree_path: Working directory for the cmux workspace.
        session_id: UUID for Claude --session-id flag (or --resume if resume=True).
        project_root: Main repo path for PROJECT_ROOT env var. If None, detected
            via git rev-parse (Task #2586).
        resume: If True, use --resume to resume existing session instead of --session-id.

    Returns:
        int: PID of the launcher process.

    Raises:
        SpawnError: If workspace creation fails.
    """
    session_name = f"task-{task_id}"
    log_file = get_claude_home() / "worker_signals.log"

    # Task #2586: Get PROJECT_ROOT for env var passing (fallback to git detection)
    if project_root is None:
        project_root = _get_main_repo_path()

    cmux.kill_session(session_name)

    try:
        env_vars = {"PROJECT_ROOT": project_root}
        if not cmux.create_session(session_name, worktree_path, env_vars=env_vars):
            raise SpawnError(f"create_session failed for task #{task_id}")

        trap_cmd = f"trap 'echo \"$(date -u +%Y-%m-%dT%H:%M:%SZ) SIGTERM task-{task_id}\" >> {shlex.quote(str(log_file))}' SIGTERM"
        if resume:
            resume_msg = (
                "RESUME CONTEXT: Your task list (TaskCreate/TaskList) was reset by session restart. "
                "Do NOT recreate tasks from the previous session. Continue from where you left off."
            )
            claude_cmd = (
                f"{trap_cmd}; "
                f"set +m; claude --permission-mode bypassPermissions --resume {shlex.quote(session_id)} "
                f"{shlex.quote(resume_msg)}"
            )
        else:
            prompt = f"#task:{task_id} - Implement following TDD workflow."
            claude_cmd = (
                f"{trap_cmd}; "
                f"set +m; claude --permission-mode bypassPermissions --session-id {shlex.quote(session_id)} "
                f"{shlex.quote(prompt)}"
            )

        if not cmux.send_keys(session_name, claude_cmd):
            raise SpawnError(f"send_keys failed for task #{task_id}")
    except SpawnError as error:
        with contextlib.suppress(Exception):
            cmux.kill_session(session_name)
        _cleanup_failed_spawn_worktree(worktree_path, task_id)
        raise error
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as error:
        with contextlib.suppress(Exception):
            cmux.kill_session(session_name)
        _cleanup_failed_spawn_worktree(worktree_path, task_id)
        raise SpawnError(f"Failed to spawn worker for task #{task_id}") from error

    return os.getpid()


def rebase_worktree_onto_target(
    worktree_path: str,
    task_id: int,
    skip_fetch: bool = False,
    target_branch: str = "origin/master",
) -> None:
    """Rebase worktree branch onto target branch with safe stash handling.

    Performs: fetch (optional) -> stash -> rebase -> stash pop
    On failure: aborts rebase, restores stash, logs warning, continues.

    Args:
        worktree_path: Path to the git worktree.
        task_id: Task ID for logging context.
        skip_fetch: If True, skip git fetch (batch optimization).
        target_branch: Branch to rebase onto (default: origin/master).
            Can be 'origin/master', 'feature/foo', or 'origin/feature/foo'.
    """
    logger = logging.getLogger(__name__)
    stash_created = False

    # Clean up stale locks from crashed git processes
    _cleanup_stale_git_locks(worktree_path)

    # Normalize target_branch for fetch: extract branch name without origin/ prefix
    if target_branch.startswith("origin/"):
        fetch_branch = target_branch[7:]  # Remove 'origin/' prefix
        rebase_target = target_branch
    else:
        fetch_branch = target_branch
        rebase_target = f"origin/{target_branch}"

    try:
        # Step 1: Fetch latest (optional)
        if not skip_fetch:
            subprocess.run(
                ["git", "fetch", "origin", fetch_branch],
                check=True,
                capture_output=True,
                cwd=worktree_path,
                timeout=30,
            )

        # Step 2: Stash uncommitted + untracked
        stash_result = subprocess.run(
            ["git", "stash", "push", "--include-untracked", "-m", "auto-rebase-stash"],
            capture_output=True,
            cwd=worktree_path,
            timeout=30,
        )
        stash_output = stash_result.stdout.decode()
        stash_created = stash_result.returncode == 0 and "No local changes" not in stash_output

        # Step 3: Rebase onto target branch
        subprocess.run(
            ["git", "rebase", rebase_target],
            check=True,
            capture_output=True,
            cwd=worktree_path,
            timeout=30,
        )

        # Step 4: Restore stash
        if stash_created:
            pop_result = subprocess.run(
                ["git", "stash", "pop"],
                capture_output=True,
                cwd=worktree_path,
                timeout=30,
            )
            if pop_result.returncode != 0:
                pop_stderr = pop_result.stderr.decode()
                logger.warning(
                    f"Stash pop had conflicts for task #{task_id}: {pop_stderr}. "
                    "Stash preserved - worker may need to resolve manually."
                )

    except subprocess.CalledProcessError as error:
        # Rebase failures should not block worker spawn - log warning and continue
        stderr = error.stderr.decode()
        logger.warning(
            f"Auto-rebase failed for task #{task_id}: {stderr}. "
            "Worker will continue with current branch state."
        )
        # Abort any in-progress rebase to clean up
        subprocess.run(
            ["git", "rebase", "--abort"],
            capture_output=True,
            cwd=worktree_path,
            timeout=30,
        )
        # Restore stashed changes even if rebase failed
        if stash_created:
            subprocess.run(
                ["git", "stash", "pop"],
                capture_output=True,
                cwd=worktree_path,
                timeout=30,
            )


def spawn_worker(
    task_id: int,
    db_path: str,
    skip_fetch: bool = False,
    fresh: bool = False,
    chain: bool = True,
    base_branch: str | None = None,
) -> int:
    """MVP: Spawn a worker process for a task.

    This is an MVP implementation that creates basic worktree + tmux session.
    Full implementation tracked in Task #493 (Sandboxed Parallel Worker Architecture).

    Args:
        task_id: The ID of the task to spawn a worker for.
        db_path: Path to SQLite database.
        skip_fetch: If True, skip git fetch (use when batch fetch already done).
        fresh: If True, clean up existing worktree/branch before recreation.
        chain: If True, touch .task/chain file to signal chaining.
        base_branch: If set, use this branch as base instead of epic's feature_branch or origin/master.
            Used for chaining to base new task on completed task's branch.

    Returns:
        int: Process ID of the spawned worker.

    Raises:
        ValueError: If task_id contains path traversal or shell metacharacters.
        ValueError: If PID cannot be parsed from tmux output (Task #673).
        SpawnError: If tmux session creation fails (with worker record cleanup).

    Implementation Notes:
        Current MVP behavior:
        - Creates git worktree at ~/.claude/worktrees/task-{id}
        - Generates UUID session_id for session tracking (Task #1802)
        - Stores session_id in .task/session_id file
        - Spawns tmux session with Claude Code --permission-mode dontAsk --session-id
        - Registers worker in database with PID

    See Also:
        ~/.claude/bin/task-worker-spawn: Bash equivalent with check-in scheduling
    """
    # Validate task_id before any filesystem operations
    validate_task_id(task_id)

    # Auto-cleanup stale worktrees before spawning new ones
    # Only cleans worktrees with merged PRs to master and no uncommitted changes
    cleanup_result = cleanup_stale_worktrees()
    if cleanup_result["count"] > 0:
        logger.info(
            "Auto-cleaned %d stale worktrees: %s",
            cleanup_result["count"],
            ", ".join(cleanup_result["deleted"]),
        )

    # Task #1956: Clean up existing worker resources if fresh=True
    if fresh:
        cleanup_existing_worker(task_id)

    # Create worktree directory
    WORKTREE_BASE.mkdir(parents=True, exist_ok=True)
    worktree_path = WORKTREE_BASE / f"task-{task_id}"

    # Create worktree with dedicated task branch (fixes corruption from using HEAD)
    # Priority: explicit base_branch > epic's feature_branch > origin/master
    branch_name = f"task-{task_id}"
    default_branch = git_utils.get_default_branch()
    feature_branch = None
    if base_branch is None:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT e.feature_branch FROM tasks t
                   JOIN epics e ON t.epic_name = e.name
                   WHERE t.id = ?""",
                (task_id,),
            )
            row = cursor.fetchone()
            feature_branch = row[0] if row and row[0] else None
            base_branch = feature_branch if feature_branch else f"origin/{default_branch}"
    if base_branch is None:
        raise ValueError("base_branch must be resolved before spawning worktree")
    spawn_base_branch: str = base_branch
    try:
        subprocess.run(
            ["git", "worktree", "add", "-b", branch_name, str(worktree_path), spawn_base_branch],
            check=True,
            capture_output=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode()
        # Handle "already exists" - try to reuse existing branch/worktree
        if "already exists" in stderr:
            # Branch exists - try adding worktree using existing branch
            try:
                subprocess.run(
                    ["git", "worktree", "add", str(worktree_path), branch_name],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
            except subprocess.CalledProcessError:
                pass  # Worktree also exists - reuse it
        else:
            raise  # Re-raise other errors

    # Task #1322: Auto-rebase worktree onto target branch
    # Use feature_branch if set, otherwise origin/master
    rebase_worktree_onto_target(str(worktree_path), task_id, skip_fetch, target_branch=base_branch)

    # Create .task/ binding directory for hook context injection
    # CRITICAL: Without this, SessionStart and UserPromptSubmit hooks can't find
    # the task ID or database path, so workers get NO task context injected
    task_binding_dir = worktree_path / ".task"
    task_binding_dir.mkdir(parents=True, exist_ok=True)

    # Write task ID for SessionStart hook (task_context_loader.py)
    (task_binding_dir / "id").write_text(str(task_id))

    # Write project root for database resolution by hooks
    # Derive from db_path instead of git rev-parse (fails when chaining from worktree)
    main_repo = str(Path(db_path).parent.parent)
    (task_binding_dir / "project_root").write_text(main_repo)

    # Check if we can resume a previous Claude session (respawn case)
    resumable_session_id = None
    if not fresh:
        resumable_session_id = _check_resumable_session(task_id, worktree_path)
        if resumable_session_id:
            logger.info("Resumable session found for task #%d: %s", task_id, resumable_session_id)

    if resumable_session_id:
        session_id = resumable_session_id
    else:
        # Task #1802: Generate session ID for Claude session tracking
        session_id = str(uuid.uuid4())
        (task_binding_dir / "session_id").write_text(session_id)

        # Task #2655: Store session_id in tasks table for transcript retrieval
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET session_id = ? WHERE id = ?",
                (session_id, task_id),
            )

    # Task #2428: Write target branch for SessionStart PR instructions
    target_branch = feature_branch if feature_branch else default_branch
    (task_binding_dir / "target_branch").write_text(target_branch)

    # Task #2374: Touch chain file if chain=True to signal autospawn chaining
    if chain:
        (task_binding_dir / "chain").touch()

    # Task #1031: Initialize TDD Guard in worktree before spawning Claude agent
    # This creates pytest.ini, config.json, and test.json for isolated test state
    setup_script = get_claude_home() / "scripts" / "setup-worktree-tdd-guard.sh"
    if setup_script.exists():
        try:
            subprocess.run(
                [str(setup_script), str(worktree_path)],
                check=True,
                capture_output=True,
                timeout=30,
            )
        except subprocess.CalledProcessError as error:
            # Log but don't fail - TDD Guard setup should not block task spawning
            stderr = (
                error.stderr.decode() if isinstance(error.stderr, bytes) else (error.stderr or "")
            )
            logging.getLogger(__name__).warning(
                f"TDD Guard setup failed for task #{task_id}: {stderr}"
            )
        except subprocess.TimeoutExpired:
            logging.getLogger(__name__).warning(f"TDD Guard setup timed out for task #{task_id}")
    else:
        logging.getLogger(__name__).debug(
            f"TDD Guard setup script not found at {setup_script}, skipping"
        )

    # Pass main_repo to avoid redundant git rev-parse call (Task #2586 simplification)
    pid = spawn_tmux_session(
        task_id,
        str(worktree_path),
        session_id,
        project_root=main_repo,
        resume=bool(resumable_session_id),
    )

    # Task #2494: Register worktree-to-task mapping for dashboard idle detection
    # Without this, get_transcript_mtime() returns None → age_seconds = inf → is_stale = True
    # Called after spawn_tmux_session() so no orphan entry if spawn fails
    set_current_task(db_path, str(worktree_path), task_id)

    # Task #2653: Worker registration removed (workers table deleted - staleness from transcript mtime)

    return pid
