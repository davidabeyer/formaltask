"""
Automated worktree cleanup with triple-verified safety checks.

This module provides safe cleanup of stale task worktrees. A worktree is
only deleted if ALL safety checks pass:

1. No uncommitted changes
2. No active tmux session
3. Has merged PR to master (or all commits ancestry-merged)
4. No open PRs
5. No unpushed local commits

Usage:
    from formaltask.git.worktree import cleanup_stale_worktrees

    # In spawn_worker(), at the start:
    cleanup_stale_worktrees()
"""

import glob
import json
import logging
import os
import subprocess
from pathlib import Path

from formaltask import cmux
from formaltask.paths import get_claude_home

logger = logging.getLogger(__name__)


def _run(cmd: list[str], cwd: str | None = None, timeout: int = 30) -> tuple[int, str, str]:
    """Run command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def check_worktree_safety(worktree_path: str) -> dict:
    """
    Check if a worktree is safe to delete.

    Returns dict with:
        - safe: bool - True only if ALL checks pass
        - reason: str - Why it's safe or unsafe
        - checks: dict - Individual check results
    """
    result = {
        "worktree": worktree_path,
        "safe": False,
        "reason": None,
        "checks": {},
    }

    wt = Path(worktree_path)
    name = wt.name

    # 0. Worktree exists
    if not wt.exists():
        result["reason"] = "Worktree directory does not exist"
        result["checks"]["exists"] = False
        return result
    result["checks"]["exists"] = True

    # 1. UNCOMMITTED CHANGES - Most important check
    rc, stdout, _ = _run(["git", "status", "--porcelain"], cwd=worktree_path)
    if stdout:
        line_count = len(stdout.splitlines())
        result["reason"] = f"Has uncommitted changes ({line_count} files)"
        result["checks"]["clean"] = False
        return result
    result["checks"]["clean"] = True

    # 2. GET BRANCH NAME
    rc, branch, _ = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=worktree_path)
    if rc != 0:
        result["reason"] = "Cannot determine branch"
        result["checks"]["branch"] = None
        return result
    result["checks"]["branch"] = branch

    # 3. ACTIVE TMUX SESSION - Fail-safe: if check fails, assume session exists
    session_name = name
    rc, _, stderr = _run(["tmux", "has-session", "-t", session_name])
    if rc == 0:
        result["reason"] = f"Active tmux session: {session_name}"
        result["checks"]["no_tmux"] = False
        return result
    if rc != 1:  # Only rc=1 means "no session" - anything else is fail-safe
        result["reason"] = f"Could not verify tmux session status (rc={rc}): {stderr}"
        result["checks"]["no_tmux"] = "unknown"
        return result
    result["checks"]["no_tmux"] = True

    if cmux.session_exists(session_name):
        result["reason"] = f"Active cmux session: {session_name}"
        result["checks"]["no_cmux"] = False
        return result
    result["checks"]["no_cmux"] = True

    # 4. CHECK FOR MERGED PR (source of truth for squash merges)
    rc, pr_json, _ = _run(
        [
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "merged",
            "--json",
            "number,baseRefName,mergedAt",
            "--limit",
            "1",
        ]
    )

    has_merged_pr = False
    merged_to_master = False
    pr_info = None

    if rc == 0 and pr_json and pr_json != "[]":
        try:
            prs = json.loads(pr_json)
            if prs:
                pr_info = prs[0]
                has_merged_pr = True
                base = pr_info.get("baseRefName", "")
                merged_to_master = base in ("master", "main")
        except json.JSONDecodeError:
            pass

    result["checks"]["has_merged_pr"] = has_merged_pr
    result["checks"]["pr_info"] = pr_info

    # 5. CHECK FOR OPEN PR (work in progress)
    rc, open_json, _ = _run(
        [
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "open",
            "--json",
            "number,title",
            "--limit",
            "1",
        ]
    )
    has_open_pr = False
    if rc == 0 and open_json and open_json != "[]":
        try:
            prs = json.loads(open_json)
            has_open_pr = bool(prs)
        except json.JSONDecodeError:
            pass

    if has_open_pr:
        result["reason"] = "Has open PR (work in progress)"
        result["checks"]["no_open_pr"] = False
        return result
    result["checks"]["no_open_pr"] = True

    # 6. VERIFY PR WAS MERGED TO MASTER (not feature branch)
    if has_merged_pr and pr_info is not None and not merged_to_master:
        base = pr_info.get("baseRefName", "unknown")
        result["reason"] = f"PR merged to {base}, not master"
        result["checks"]["merged_to_master"] = False
        return result
    result["checks"]["merged_to_master"] = merged_to_master if has_merged_pr else "N/A"

    # 7. IF NO MERGED PR, CHECK GIT ANCESTRY (fallback for regular merges)
    if not has_merged_pr:
        # Fetch first (ignore errors)
        _run(["git", "fetch", "origin", "master", "--quiet"], cwd=worktree_path)
        # Check ancestry
        rc, _, _ = _run(
            ["git", "merge-base", "--is-ancestor", "HEAD", "origin/master"],
            cwd=worktree_path,
        )
        if rc == 0:
            result["checks"]["ancestry_merged"] = True
        else:
            result["reason"] = "No merged PR and commits not in master"
            result["checks"]["ancestry_merged"] = False
            return result

    # 8. LOCAL-ONLY COMMITS (pushed but more work done locally)
    rc, local_commits, _ = _run(
        ["git", "log", f"origin/{branch}..HEAD", "--oneline"],
        cwd=worktree_path,
    )
    # If command fails (branch not on origin), treat as no local commits
    if rc != 0:
        local_commits = ""
    if local_commits:
        count = len(local_commits.splitlines())
        result["reason"] = f"Has {count} unpushed commits"
        result["checks"]["no_local_commits"] = False
        return result
    result["checks"]["no_local_commits"] = True

    # ALL CHECKS PASSED
    result["safe"] = True
    if has_merged_pr and pr_info is not None:
        result["reason"] = f"PR #{pr_info['number']} merged to master"
    else:
        result["reason"] = "All commits in master (ancestry)"

    return result


def cleanup_single_worktree(worktree_path: str, dry_run: bool = False) -> dict:
    """
    Clean up a single worktree if safe.

    Returns dict with:
        - deleted: bool
        - reason: str
        - checks: dict (from safety check)
    """
    safety = check_worktree_safety(worktree_path)

    if not safety["safe"]:
        return {
            "deleted": False,
            "reason": safety["reason"],
            "checks": safety["checks"],
        }

    if dry_run:
        return {
            "deleted": False,
            "reason": f"Would delete (dry run): {safety['reason']}",
            "checks": safety["checks"],
        }

    # Actually delete
    wt = Path(worktree_path)
    name = wt.name

    rc, _, stderr = _run(["git", "worktree", "remove", worktree_path])
    if rc != 0:
        return {
            "deleted": False,
            "reason": f"git worktree remove failed: {stderr}",
            "checks": safety["checks"],
        }

    # Try to delete branch (may fail if already deleted, that's ok)
    branch = safety["checks"].get("branch", name)
    _run(["git", "branch", "-d", branch])

    return {
        "deleted": True,
        "reason": safety["reason"],
        "checks": safety["checks"],
    }


def cleanup_stale_worktrees(dry_run: bool = False) -> dict:
    """
    Clean up all stale task worktrees that are safe to delete.

    This is designed to be called at the start of spawn_worker() to
    automatically clean up merged worktrees before creating new ones.

    Args:
        dry_run: If True, only report what would be deleted

    Returns:
        dict with:
            - deleted: list of deleted worktree names
            - skipped: list of (name, reason) tuples
            - count: number deleted
    """
    worktree_base = str(get_claude_home() / "worktrees")
    pattern = os.path.join(worktree_base, "task-*")

    deleted = []
    skipped = []

    for wt_path in glob.glob(pattern):
        if not os.path.isdir(wt_path):
            continue

        name = os.path.basename(wt_path)
        result = cleanup_single_worktree(wt_path, dry_run=dry_run)

        if result["deleted"]:
            deleted.append(name)
            logger.info("Cleaned up stale worktree: %s (%s)", name, result["reason"])
        else:
            skipped.append((name, result["reason"]))
            logger.debug("Kept worktree %s: %s", name, result["reason"])

    return {
        "deleted": deleted,
        "skipped": skipped,
        "count": len(deleted),
    }


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        dry_run = "--dry-run" in sys.argv
        result = cleanup_stale_worktrees(dry_run=dry_run)
        print(f"Deleted: {result['count']}")
        for name in result["deleted"]:
            print(f"  {name}")
        if result["skipped"]:
            print(f"\nSkipped: {len(result['skipped'])}")
            for name, reason in result["skipped"]:
                print(f"  {name}: {reason}")
    elif len(sys.argv) > 1:
        result = check_worktree_safety(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        print("Usage:")
        print("  python -m formaltask.git.worktree <worktree_path>  # Check single")
        print("  python -m formaltask.git.worktree --all            # Clean all")
        print("  python -m formaltask.git.worktree --all --dry-run  # Preview")
