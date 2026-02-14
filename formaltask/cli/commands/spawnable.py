"""pm spawnable - Show tasks ready to spawn and why others are blocked."""

import json
from dataclasses import dataclass, field

from formaltask.cli.context import with_db_path
from formaltask.core.completion_state import fetch_completion_state
from formaltask.db.connection import DatabaseConnection
from formaltask.db.helpers import parse_depends_on
from formaltask.git.github import get_prs_for_tasks
from formaltask.git.status import get_commits_ahead_of_main
from formaltask.paths import task_worktree
from formaltask.tmux import get_all_task_sessions
from formaltask.utils.constants import TaskStatus
from formaltask.validators.file_conflict import extract_files_from_spec


def setup_parser(subparser):
    """Set up argument parser for spawnable command."""
    subparser.add_argument("--db-path", default=None, help="Database path")
    subparser.add_argument(
        "--why",
        type=int,
        metavar="TASK_ID",
        help="Show why a specific task is blocked",
    )
    subparser.add_argument(
        "--complete",
        action="store_true",
        help="Show completion blockers (use with --why)",
    )


@dataclass
class Blocker:
    """Why a task can't spawn."""

    reason: str
    detail: str = ""


@dataclass
class TaskSpawnInfo:
    """Task spawn status with blockers."""

    id: int
    title: str
    epic_name: str
    blockers: list[Blocker] = field(default_factory=list)
    merged_pr: int | None = None

    @property
    def can_spawn(self) -> bool:
        return not self.blockers


def _extract_spec_files(metadata_json: str | None) -> set[str]:
    """Extract file paths from spec metadata JSON."""
    if not metadata_json:
        return set()
    try:
        m = json.loads(metadata_json)
        if m.get("artifact_type") == "spec" and m.get("artifact_content"):
            return extract_files_from_spec(m["artifact_content"])
    except (json.JSONDecodeError, TypeError):
        pass
    return set()


def _worktree_exists(task_id: int) -> str:
    """Check if worktree exists. Returns path or empty string."""
    try:
        wt = task_worktree(task_id)
        return str(wt) if wt.exists() else ""
    except OSError:
        return ""


def spawnable(db_path: str) -> list[TaskSpawnInfo]:  # noqa: C901
    """Get spawn status for all open tasks. Returns TaskSpawnInfo with blockers."""
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        # Query 1: Files touched by in-progress tasks
        cursor.execute("SELECT metadata FROM tasks WHERE status = ?", (TaskStatus.IN_PROGRESS,))
        in_progress_files: set[str] = set()
        for (metadata_json,) in cursor.fetchall():
            in_progress_files.update(_extract_spec_files(metadata_json))

        # Query 2: All open tasks from non-archived epics
        cursor.execute(
            """
            SELECT t.id, t.title, t.epic_name, t.depends_on, t.metadata
            FROM tasks t JOIN epics e ON t.epic_name = e.name
            WHERE e.archived_at IS NULL AND t.status = ?
            ORDER BY t.id
        """,
            (TaskStatus.OPEN,),
        )
        tasks_data = cursor.fetchall()
        if not tasks_data:
            return []

        # Collect dependency IDs
        all_dep_ids: set[int] = set()
        for _, _, _, dj, _ in tasks_data:
            all_dep_ids.update(parse_depends_on(dj))

        # Query 3: Batch fetch dependencies
        deps_by_id: dict[int, dict] = {}
        if all_dep_ids:
            ph = ",".join("?" * len(all_dep_ids))
            # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
            cursor.execute(
                f"SELECT id, title, status, epic_name FROM tasks WHERE id IN ({ph})",
                list(all_dep_ids),
            )
            deps_by_id = {
                r[0]: {"title": r[1], "status": r[2], "epic": r[3]} for r in cursor.fetchall()
            }

    # Process in memory
    results = []
    for task_id, title, epic_name, depends_on_json, metadata_json in tasks_data:
        blockers = []
        # Worktree exists?
        if wt := _worktree_exists(task_id):
            blockers.append(Blocker("worktree exists", wt))
        # File overlap?
        overlap = (
            _extract_spec_files(metadata_json) & in_progress_files if in_progress_files else set()
        )
        if overlap:
            files = ", ".join(sorted(overlap)[:3]) + (
                f" +{len(overlap) - 3} more" if len(overlap) > 3 else ""
            )
            blockers.append(Blocker("file overlap", files))
        # Dependencies?
        for dep_id in parse_depends_on(depends_on_json):
            dep = deps_by_id.get(dep_id)
            if not dep:
                blockers.append(Blocker(f"dep #{dep_id} not found", ""))
            elif dep["status"] != TaskStatus.COMPLETED:
                blockers.append(Blocker(f"dep #{dep_id} {dep['status']}", dep["title"]))
        results.append(
            TaskSpawnInfo(id=task_id, title=title, epic_name=epic_name, blockers=blockers)
        )
    return results


def _detect_orphan_tasks(db_path) -> list[TaskSpawnInfo]:
    """Find in_progress tasks with no tmux session or worktree.

    Returns list of TaskSpawnInfo with merged_pr populated if PR was merged.
    """
    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, epic_name FROM tasks WHERE status = ?",
            (TaskStatus.IN_PROGRESS,),
        )
        in_progress = cursor.fetchall()

    if not in_progress:
        return []

    # Get active tmux sessions
    active_sessions = set(get_all_task_sessions())

    # Check each in_progress task
    orphans: list[TaskSpawnInfo] = []
    task_ids_to_check: list[int] = []
    for task_id, title, epic_name in in_progress:
        session_name = f"task-{task_id}"
        has_tmux = session_name in active_sessions
        has_worktree = bool(_worktree_exists(task_id))

        if not has_tmux and not has_worktree:
            orphans.append(TaskSpawnInfo(id=task_id, title=title, epic_name=epic_name))
            task_ids_to_check.append(task_id)

    # Check for merged PRs on orphan tasks
    if task_ids_to_check:
        try:
            prs = get_prs_for_tasks(task_ids_to_check)
            for orphan in orphans:
                pr = prs.get(orphan.id)
                if pr and pr.merged:
                    orphan.merged_pr = pr.number
        except Exception:
            # GitHub CLI failure shouldn't crash orphan detection
            # merged_pr remains None for all orphans
            pass

    return orphans


def _detect_orphan_commits(blocked: list[TaskSpawnInfo]) -> list[tuple[int, int, str]]:
    """Detect orphan commits: worktree exists + PR merged + commits ahead > 0.

    Args:
        blocked: List of blocked tasks to check for orphan commits.

    Returns:
        List of (task_id, commits_ahead, worktree_path) tuples for tasks
        with orphan commits (commits pushed after PR was merged).
    """
    # Collect tasks with worktrees from blockers
    worktree_tasks: dict[int, str] = {}  # task_id -> worktree_path
    for t in blocked:
        for b in t.blockers:
            if b.reason == "worktree exists" and b.detail:
                worktree_tasks[t.id] = b.detail
                break

    if not worktree_tasks:
        return []

    # Check PR status and commits ahead for tasks with worktrees
    orphan_warnings: list[tuple[int, int, str]] = []
    prs = get_prs_for_tasks(list(worktree_tasks.keys()))
    for task_id, worktree_path in worktree_tasks.items():
        pr = prs.get(task_id)
        if pr and pr.merged:
            commits_ahead = get_commits_ahead_of_main(worktree_path)
            if commits_ahead > 0:
                orphan_warnings.append((task_id, commits_ahead, worktree_path))

    return orphan_warnings


def _execute_why(db_path: str, task_id: int, show_complete: bool) -> int:
    """Show why a specific task is blocked (--why mode)."""
    blockers: list[str] = []

    with DatabaseConnection(db_path) as conn:
        cursor = conn.cursor()

        # Check task exists and get its data
        cursor.execute(
            "SELECT status, metadata FROM tasks WHERE id = ?",
            (task_id,),
        )
        row = cursor.fetchone()
        if not row:
            print(f"Task #{task_id} not found")
            return 1

        _, metadata_json = row

        # 1. Check dependency blockers from view
        cursor.execute(
            "SELECT blocking_task_ids FROM task_blocked_status WHERE task_id = ?",
            (task_id,),
        )
        row = cursor.fetchone()
        if row and row[0]:
            blocking_ids = json.loads(row[0])
            for bid in blocking_ids:
                blockers.append(f"  - Dependency #{bid} incomplete -> Wait for #{bid} to complete")

        # 2. Check worktree exists
        if wt := _worktree_exists(task_id):
            blockers.append(f"  - Worktree exists ({wt}) -> Remove worktree first")

        # 3. Check file conflicts with in-progress tasks
        cursor.execute("SELECT metadata FROM tasks WHERE status = ?", (TaskStatus.IN_PROGRESS,))
        in_progress_files: set[str] = set()
        for (md,) in cursor.fetchall():
            in_progress_files.update(_extract_spec_files(md))

        task_files = _extract_spec_files(metadata_json)
        overlap = task_files & in_progress_files
        if overlap:
            files_str = list(overlap)[0]
            blockers.append(f"  - File overlap with in-progress task -> Wait (touches {files_str})")

    # Handle --complete: show completion blockers
    completion_blockers: list[str] = []
    if show_complete:
        state = fetch_completion_state(task_id, db_path)
        if state and not state.get("closed"):
            if state.get("missing_reviews"):
                missing = ", ".join(sorted(state["missing_reviews"]))
                completion_blockers.append(
                    f"  - Missing reviews: {missing} -> Run required reviews"
                )
            if state.get("blocking_findings"):
                count = len(state["blocking_findings"])
                completion_blockers.append(
                    f"  - {count} blocking finding(s) -> Address review findings"
                )
            if state.get("require_pr") and not state.get("has_pr"):
                completion_blockers.append("  - PR not created -> Run: gh pr create")
            if state.get("stale_reviews"):
                stale = ", ".join(sorted(state["stale_reviews"]))
                completion_blockers.append(f"  - Stale reviews: {stale} -> Re-run reviews")

    # Output
    if show_complete:
        if completion_blockers:
            print(f"Task #{task_id} cannot complete:")
            for b in completion_blockers:
                print(b)
        else:
            print(f"Task #{task_id} ready to complete (no completion blockers)")
            print()
            print(f"Run: ft task complete {task_id}")
    elif blockers:
        print(f"Task #{task_id} blocked:")
        for b in blockers:
            print(b)
        print()
        print(f"Run: ft work spawn {task_id} (after blockers clear)")
    else:
        print(f"Task #{task_id} ready to spawn (no blockers)")
        print()
        print(f"Run: ft work spawn {task_id}")

    return 0


@with_db_path
def execute(db_path: str, args) -> int:
    """Execute the spawnable command."""
    # Handle --why mode: show blockers for specific task
    if getattr(args, "why", None):
        return _execute_why(db_path, args.why, getattr(args, "complete", False))

    tasks = spawnable(db_path)
    ready, blocked = [t for t in tasks if t.can_spawn], [t for t in tasks if not t.can_spawn]
    has_output = False

    if ready:
        print("Ready:")
        for t in ready:
            print(f"  #{t.id}\t{t.epic_name}\t{t.title}")
        has_output = True

    if blocked:
        if has_output:
            print()
        print("Blocked:")
        for t in blocked:
            print(f"  #{t.id}\t{t.epic_name}\t{t.title}")
            for b in t.blockers:
                print(f"    -> {b.reason}" + (f" ({b.detail})" if b.detail else ""))
        has_output = True

    orphan_warnings = _detect_orphan_commits(blocked)
    if orphan_warnings:
        if has_output:
            print()
        print("Orphan Commits:")
        for task_id, commits, path in orphan_warnings:
            print(f"  \u26a0\ufe0f #{task_id}: {commits} commit(s) after merged PR in {path}")
        has_output = True

    orphan_tasks = _detect_orphan_tasks(db_path)
    if orphan_tasks:
        if has_output:
            print()
        print("Orphaned (in_progress but no worker):")
        for orphan in orphan_tasks:
            pr_info = f" (PR #{orphan.merged_pr} MERGED)" if orphan.merged_pr else ""
            print(f"  \u26a0\ufe0f #{orphan.id}\t{orphan.epic_name}\t{orphan.title}{pr_info}")
        has_output = True

    if not has_output:
        print("No open tasks")
    return 0
