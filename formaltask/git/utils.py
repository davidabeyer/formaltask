"""Shared git utilities."""

import os
import subprocess
from pathlib import Path


def _get_git_env() -> dict[str, str]:
    """Get environment with LC_ALL=C for consistent output."""
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    return env


def _validate_git_arg(arg: str) -> None:
    """Validate git argument for injection prevention.

    Allows standard flags (-e, --is-ancestor) but rejects potentially dangerous
    options with arguments (--upload-pack=..., --exec=...).
    """
    # Allow short flags (single dash)
    if arg.startswith("-") and not arg.startswith("--"):
        return
    # Whitelist safe format options (--format=%B, --pretty=%s, etc.)
    if arg.startswith(("--format=", "--pretty=")):
        return
    # Reject other long options with = (potential code injection)
    if arg.startswith("--") and "=" in arg:
        raise ValueError(f"Invalid git argument: {arg}")


def _run_git_command(
    args: list[str],
    repo_path: Path | None = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess | None:
    """Run git command with security and timeout."""
    for arg in args:
        _validate_git_arg(arg)
    cmd = ["git"]
    if repo_path:
        cmd.extend(["-C", str(repo_path)])
    cmd.extend(args)
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, env=_get_git_env()
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def get_head_sha(repo_path: Path | None = None) -> str | None:
    """Get current HEAD SHA. Returns None on error."""
    result = _run_git_command(["rev-parse", "HEAD"], repo_path)
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def commit_exists(commit: str, repo_path: Path | None = None) -> bool:
    """Check if commit exists in repo.

    Raises:
        ValueError: If commit ref starts with '-' (prevents git argument injection)
    """
    if commit.startswith("-"):
        raise ValueError(f"commit ref cannot start with '-': {commit}")
    result = _run_git_command(["cat-file", "-e", commit], repo_path)
    return result is not None and result.returncode == 0


def is_ancestor(commit: str, target: str = "HEAD", repo_path: Path | None = None) -> bool | None:
    """Check if commit is ancestor of target. Returns None on error.

    Raises:
        ValueError: If commit or target ref starts with '-' (prevents git argument injection)
    """
    if target.startswith("-"):
        raise ValueError(f"target ref cannot start with '-': {target}")
    if not commit_exists(commit, repo_path):
        return None
    result = _run_git_command(["merge-base", "--is-ancestor", commit, target], repo_path)
    if result is None:
        return None
    return result.returncode == 0


def fetch_remote(
    remote: str = "origin",
    branch: str | None = None,
    repo_path: Path | None = None,
    timeout: int = 10,
) -> bool:
    """Fetch from remote to update local refs.

    Gracefully handles network errors - returns False instead of raising.
    Used to ensure origin/master ref is current before ancestry checks.

    Args:
        remote: Remote name (default: "origin")
        branch: Specific branch to fetch (default: all branches)
        repo_path: Optional repository path
        timeout: Fetch timeout in seconds (default: 10, shorter for advisory checks)

    Returns:
        True if fetch succeeded, False on any error (network, timeout, etc.)
    """
    cmd = ["fetch", remote]
    if branch:
        cmd.append(branch)

    try:
        result = _run_git_command(cmd, repo_path, timeout=timeout)
        return result is not None and result.returncode == 0
    except OSError:
        # System-level errors (PermissionError, etc.) not caught by _run_git_command
        return False


def get_default_branch(repo_path: Path | None = None) -> str:
    """Get the default branch name for origin remote.

    Detects the default branch by:
    1. Checking git symbolic-ref refs/remotes/origin/HEAD
    2. Falling back to 'main' if refs/remotes/origin/main exists
    3. Falling back to 'master' otherwise

    Returns:
        Branch name (without 'origin/' prefix), e.g., 'main' or 'master'
    """
    # Try symbolic-ref first (most reliable when set)
    result = _run_git_command(["symbolic-ref", "refs/remotes/origin/HEAD"], repo_path)
    if result and result.returncode == 0:
        ref = result.stdout.strip()
        # refs/remotes/origin/main -> main
        # P3 FIX: Use removeprefix to handle branch names containing slashes (e.g., feature/foo)
        prefix = "refs/remotes/origin/"
        if ref.startswith(prefix):
            return ref.removeprefix(prefix)

    # Check if origin/main exists
    result = _run_git_command(["rev-parse", "--verify", "origin/main"], repo_path)
    if result and result.returncode == 0:
        return "main"

    # Fallback to master
    return "master"


def find_task_in_commits(
    task_id: int,
    limit: int = 100,
    repo_path: Path | None = None,
    target: str | None = None,
) -> bool:
    """Search recent commit messages for task ID reference.

    Used as fallback when original commit SHA is not an ancestor
    (squash merge rewrites history but preserves task reference).

    Searches for all common task reference patterns:
    - "Task #1234" - explicit task reference
    - "(#1234)" - parenthesized (PR/issue style, common in squash merges)
    - "task-1234" - branch name references in merge commits

    Args:
        task_id: Task ID to search for
        limit: Max commits to search (default 100)
        repo_path: Optional repository path (default: current directory)
        target: Branch/ref to search (default: HEAD). Use "origin/master" to
               search the remote branch when local HEAD may be behind.

    Returns:
        True if task ID found in commit messages, False otherwise.
        Returns False on any git error (never raises).
    """
    import re

    # Multi-pattern search: Task #X, (#X), task-X
    # Uses extended regex alternation for efficient single git call
    grep_pattern = f"Task #{task_id}|\\(#{task_id}\\)|task-{task_id}"
    # Use --format=%B to get full commit message (subject + body) for verification
    # --oneline only returns subject line which may not contain the task reference
    cmd = ["log", "-n", str(limit), "--extended-regexp", "--grep", grep_pattern, "--format=%B"]
    if target:
        cmd.append(target)
    result = _run_git_command(
        cmd,
        repo_path=repo_path,
    )
    if not result or not result.stdout.strip():
        return False

    # Verify exact match to avoid false positives (e.g., #1 matching #100)
    # Pattern matches: "Task #1234", "(#1234)", "task-1234" with word boundaries
    exact_pattern = rf"(?:Task #|[\(\[]#|task-){task_id}(?![0-9])"
    return bool(re.search(exact_pattern, result.stdout, re.IGNORECASE))


def find_pr_in_commits(
    pr_number: int,
    limit: int = 100,
    repo_path: Path | None = None,
    target: str | None = None,
) -> bool:
    """Search recent commit messages for PR number reference."""
    import re

    # Search for (#PR) pattern - GitHub's squash merge format
    grep_pattern = f"\\(#{pr_number}\\)"
    cmd = ["log", "-n", str(limit), "--extended-regexp", "--grep", grep_pattern, "--format=%B"]
    if target:
        cmd.append(target)
    result = _run_git_command(cmd, repo_path=repo_path)
    if not result or not result.stdout.strip():
        return False

    # Verify exact match to avoid false positives
    exact_pattern = rf"\(#{pr_number}\)(?![0-9])"
    return bool(re.search(exact_pattern, result.stdout))
