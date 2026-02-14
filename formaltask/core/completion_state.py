"""Gather completion state. All side effects here (Task #2734)."""

import logging
import re
import sqlite3
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from formaltask.core import rules_config as rules
from formaltask.core.completion_config import (
    CompletionConfig,
    _parse_metadata,
    get_effective_config,
)
from formaltask.db.connection import DatabaseConnection
from formaltask.exceptions import TaskNotFoundError
from formaltask.state.findings import check_findings_state, get_findings_with_disposition
from formaltask.utils.constants import DispositionType

if TYPE_CHECKING:
    from formaltask.git.github import PRInfo

logger = logging.getLogger(__name__)


def fetch_completion_state(
    task_id: int, db_path: str | Path, *, lightweight: bool = False
) -> dict | None:
    """Fetch all state needed for completion check.

    Args:
        task_id: Task ID to check.
        db_path: Path to the database.
        lightweight: Skip expensive subprocess calls (stale reviews, AC commands).
            Use True for dashboard polling, False for ft task complete gate.

    Returns dict with state keys, or None if task doesn't exist.
    """
    db_path = Path(db_path) if isinstance(db_path, str) else db_path

    # Get effective config ONCE at top (Task #2821 single-authority pattern)
    try:
        config = get_effective_config(task_id, db_path)
    except TaskNotFoundError:
        return None

    with DatabaseConnection(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, metadata FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return None

        status = row[0]
        metadata = _parse_metadata(row[1])

        # Early exit for closed tasks
        if status in ("cancelled", "completed"):
            return {"status": status, "closed": True}

        # Early exit for blocked tasks — skip expensive PR/AC/git checks
        if status == "blocked_user":
            return {"status": status, "closed": False, "blocked": True}

        # Gather findings state
        findings_state = check_findings_state(task_id, db_path)

        # Get present reviews
        cursor.execute(
            "SELECT DISTINCT review_type FROM task_reviews WHERE task_id = ?",
            (task_id,),
        )
        present_reviews = {r[0] for r in cursor.fetchall()}

        # Get max round per review type (for task-level rule evaluation)
        cursor.execute(
            "SELECT review_type, MAX(round) FROM task_reviews WHERE task_id = ? GROUP BY review_type",
            (task_id,),
        )
        review_rounds = {row[0]: row[1] for row in cursor.fetchall()}

        # Get required reviews from config (single source of truth)
        required_reviews = set(config.required_reviews)

        # Get stale reviews (if freshness check enabled, skip in lightweight mode)
        stale_reviews = (
            _get_stale_reviews(task_id, cursor, required_reviews)
            if config.check_freshness and not lightweight
            else set()
        )

        # Get all findings once and pass to helpers (Task #2743)
        all_findings = get_findings_with_disposition(task_id, db_path)

        # Get blocking findings
        blocking_findings = _get_blocking_findings(all_findings)

        # Check low findings limit
        low_findings_exceeded = _check_low_findings_exceeded(all_findings)

        # Get PR state
        pr_state, pr_info = _get_pr_state(task_id, config)

        # Check documentation requirement
        has_docs = True
        if config.check_docs and config.documentation_required:
            has_docs = _has_doc_commits(task_id, cursor)

        # Pre-compute dynamic reasons for rules engine
        blocking_reason = None
        if blocking_findings:
            priorities = {f["priority"] for f in blocking_findings}
            blocking_reason = f"Blocking findings: {len(blocking_findings)} {', '.join(sorted(priorities))} issues"

        missing_reviews = required_reviews - present_reviews
        missing_reason = (
            f"Missing required reviews: {', '.join(sorted(missing_reviews))}"
            if missing_reviews
            else None
        )

        stale_reason = (
            f"Stale reviews: {', '.join(stale_reviews)}. Re-run reviews." if stale_reviews else None
        )

        # Execute acceptance criteria commands (Task #2860, skip in lightweight mode)
        ac_results: dict = {"passed": [], "failed": []}
        ac_failed = False
        ac_failed_reason = None
        if config.check_ac and not lightweight:
            acceptance_criteria = _get_acceptance_criteria(task_id, cursor)
            if acceptance_criteria:
                ac_results = _execute_ac_commands(acceptance_criteria)
                ac_failed = len(ac_results["failed"]) > 0
                if ac_failed:
                    ac_failed_reason = _format_ac_failed_reason(ac_results["failed"])

        return {
            "status": status,
            "closed": False,
            "blocked": False,
            "check_docs": config.check_docs and config.documentation_required,
            "has_docs": has_docs,
            "check_learnings": config.check_learnings,
            "has_learnings": bool(metadata.get("learnings")),
            "has_reviews": findings_state.has_reviews,
            "blocking_findings": blocking_findings,
            "blocking_reason": blocking_reason,
            "has_needshuman": findings_state.has_needshuman_critical,
            "low_findings_exceeded": low_findings_exceeded,
            "required_reviews": required_reviews,
            "present_reviews": present_reviews,
            "missing_reviews": missing_reviews,
            "missing_reason": missing_reason,
            "stale_reviews": stale_reviews,
            "stale_reason": stale_reason,
            # Review round counts and task-level rules
            "review_rounds": review_rounds,
            "completion_rules": metadata.get("completion_rules", []),
            # PR state
            **pr_state,
            "pr_info": pr_info,
            # AC state (Task #2860)
            "check_ac": config.check_ac,
            "ac_results": ac_results,
            "ac_failed": ac_failed,
            "ac_failed_reason": ac_failed_reason,
        }


def _has_doc_commits(task_id: int, cursor) -> bool:
    """Check if task has any .md file commits."""
    try:
        cursor.execute(
            """SELECT DISTINCT file_path FROM commit_files cf
               JOIN commits c ON cf.commit_sha = c.commit_hash
               WHERE c.task_id = ?""",
            (task_id,),
        )
    except sqlite3.OperationalError:
        # commit_files table doesn't exist - fail open
        return True
    files = {row[0] for row in cursor.fetchall()}
    return any(f.endswith(".md") for f in files)


def _get_blocking_findings(findings: list[dict]) -> list[dict]:
    """Get findings that block completion."""
    return [
        f
        for f in findings
        if f["priority"] in rules.BLOCK_PRIORITIES
        and f["disposition"]
        not in (DispositionType.WONTFIX, DispositionType.FIXED, DispositionType.NEEDSHUMAN)
    ]


def _check_low_findings_exceeded(findings: list[dict]) -> bool:
    """Check if too many low-priority findings."""
    if rules.MAX_LOW_PRIORITY_FINDINGS is None:
        return False

    low_findings = [
        f
        for f in findings
        if f["priority"] not in rules.BLOCK_PRIORITIES
        and f["disposition"] not in (DispositionType.WONTFIX, DispositionType.FIXED)
    ]
    return len(low_findings) > rules.MAX_LOW_PRIORITY_FINDINGS


def _get_stale_reviews(task_id: int, cursor, required_reviews: set) -> set:
    """Get set of stale review types."""
    from formaltask.git.utils import get_head_sha
    from formaltask.utils.subprocess import build_subprocess_env

    current_sha = get_head_sha()
    if not current_sha:
        return set()

    # Get latest SHA for each review type
    cursor.execute(
        """SELECT review_type, reviewed_sha FROM task_reviews
           WHERE task_id = ? AND (review_type, round) IN (
               SELECT review_type, MAX(round) FROM task_reviews
               WHERE task_id = ? GROUP BY review_type
           )""",
        (task_id, task_id),
    )
    review_shas = {r[0]: r[1] for r in cursor.fetchall()}

    stale_reviews = []
    for review_type in required_reviews:
        reviewed_sha = review_shas.get(review_type)
        is_fresh = False

        if reviewed_sha:
            if reviewed_sha == current_sha:
                is_fresh = True
            elif re.match(r"^[0-9a-f]{40}$", reviewed_sha) and re.match(
                r"^[0-9a-f]{40}$", current_sha
            ):
                # Get files changed between reviewed_sha and current_sha
                try:
                    result = subprocess.run(
                        ["git", "diff", "--name-only", f"{reviewed_sha}..{current_sha}"],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        env=build_subprocess_env(),
                    )
                    if result.returncode == 0:
                        changed_files = [f for f in result.stdout.strip().split("\n") if f]
                        code_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".sh"}
                        is_fresh = not any(Path(f).suffix in code_extensions for f in changed_files)
                except (subprocess.TimeoutExpired, OSError):
                    pass

        if not is_fresh:
            stale_reviews.append(review_type)

    return set(stale_reviews)


def _get_pr_state(task_id: int, config: CompletionConfig) -> tuple[dict, "PRInfo | None"]:
    """Get PR state with graceful error handling.

    Args:
        task_id: Task ID for PR lookup.
        config: CompletionConfig with require_pr and require_pr_merged settings.

    Returns:
        Tuple of (state_dict, pr_info). pr_info is preserved for callers
        that need PR number/status (e.g., dashboard health display).
    """
    from formaltask.git.github import get_pr_for_task

    try:
        pr_info = get_pr_for_task(task_id)
    except (OSError, ValueError, KeyError, RuntimeError) as e:
        logger.debug("GitHub PR query failed for task %d: %s", task_id, e)
        pr_info = None

    state = {
        "has_pr": pr_info is not None and pr_info.state != "CLOSED",
        "pr_merged": pr_info is not None and pr_info.merged,
        "pr_closed": pr_info is not None and pr_info.state == "CLOSED",
        "require_pr": config.require_pr,
        "require_pr_merged": config.require_pr_merged,
    }
    return (state, pr_info)


def _get_acceptance_criteria(task_id: int, cursor) -> list[dict]:
    """Fetch acceptance criteria from database.

    Returns list of dicts with 'text' and optional 'command' keys.
    """
    try:
        cursor.execute(
            "SELECT text, command FROM acceptance_criteria WHERE task_id = ? ORDER BY id",
            (task_id,),
        )
        return [{"text": row[0], "command": row[1]} for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        # acceptance_criteria table doesn't exist - return empty
        return []


def _format_ac_failed_reason(failed: list[dict]) -> str:
    """Format AC failed reason with command output."""
    lines = ["Acceptance criteria command(s) failed:"]
    for f in failed:
        lines.append(f"  - {f['criterion_id']}: command '{f['command']}' exited {f['exit_code']}")
        if f.get("stderr"):
            stderr_preview = f["stderr"].strip()[:200]
            if stderr_preview:
                lines.append(f"    stderr: {stderr_preview}")
    return "\n".join(lines)


def _execute_ac_commands(criteria: list[dict]) -> dict:
    """Execute acceptance criteria commands and return results.

    Args:
        criteria: List of dicts with 'text', optional 'id', and optional 'command' keys.

    Returns:
        Dict with 'passed' (list of criterion ids) and 'failed' (list of failure dicts).
    """
    from formaltask.utils.subprocess import build_subprocess_env

    passed: list[str] = []
    failed: list[dict] = []

    for criterion in criteria:
        command = criterion.get("command")
        if not command:
            continue

        criterion_id = criterion.get("id", criterion["text"])

        try:
            # shell=True required: AC commands are user-defined shell commands
            result = subprocess.run(
                command,
                shell=True,  # nosemgrep: python.lang.security.audit.subprocess-shell-true.subprocess-shell-true
                capture_output=True,
                text=True,
                timeout=300,
                env=build_subprocess_env(),
            )
            if result.returncode == 0:
                passed.append(criterion_id)
            else:
                failed.append(
                    {
                        "criterion_id": criterion_id,
                        "command": command,
                        "exit_code": result.returncode,
                        "stderr": result.stderr,
                    }
                )
        except subprocess.TimeoutExpired:
            failed.append(
                {
                    "criterion_id": criterion_id,
                    "command": command,
                    "exit_code": -1,
                    "stderr": "Command timed out after 300 seconds",
                    "timeout": True,
                }
            )
        except OSError as e:
            failed.append(
                {
                    "criterion_id": criterion_id,
                    "command": command,
                    "exit_code": -1,
                    "stderr": f"OS error: {e}",
                }
            )

    return {"passed": passed, "failed": failed}
