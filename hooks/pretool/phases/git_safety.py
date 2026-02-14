"""Comprehensive git/filesystem safety guard.

Blocks destructive commands that can lose uncommitted work or delete files.
Based on hooks/git_safety_guard.py - now wired into pretool runner.

Source: https://github.com/Dicklesworthstone/misc_coding_agent_tips_and_scripts
Incident: December 17, 2025 - AI agent ran `git checkout --` destroying hours of work
"""

import re

# Destructive patterns to block - tuple of (regex, reason)
DESTRUCTIVE_PATTERNS = [
    # Git commands that discard uncommitted changes
    (
        r"git\s+checkout\s+--\s+",
        "git checkout -- discards uncommitted changes permanently. Use 'git stash' first.",
    ),
    (
        r"git\s+checkout\s+(?!-b\b)(?!--orphan\b)[^\s]+\s+--\s+",
        "git checkout <ref> -- <path> overwrites working tree. Use 'git stash' first.",
    ),
    (
        r"git\s+restore\s+(?!--staged\b)[^\s]*\s*$",
        "git restore discards uncommitted changes. Use 'git stash' or 'git diff' first.",
    ),
    (
        r"git\s+restore\s+--worktree",
        "git restore --worktree discards uncommitted changes permanently.",
    ),
    # Git reset variants
    (
        r"git\s+reset\s+.*--hard",
        "git reset --hard destroys uncommitted changes. Use 'git stash' first.",
    ),
    (r"git\s+reset\s+--merge", "git reset --merge can lose uncommitted changes."),
    # Git clean
    (
        r"git\s+clean\s+-[a-z]*f",
        "git clean -f removes untracked files permanently. Review with 'git clean -n' first.",
    ),
    # Force push operations
    (
        r"git\s+push\s+.*--force(?!-with-lease)",
        "Force push can destroy remote history. Use --force-with-lease if necessary.",
    ),
    (
        r"git\s+push\s+-f\b",
        "Force push (-f) can destroy remote history. Use --force-with-lease if necessary.",
    ),
    (r"git\s+branch\s+-D\b", "git branch -D force-deletes without merge check. Use -d for safety."),
    # Destructive filesystem commands
    (
        r"rm\s+-[a-z]*r[a-z]*f|rm\s+-[a-z]*f[a-z]*r",
        "rm -rf is destructive. List files first, then delete individually with permission.",
    ),
    (r"rm\s+-rf\s+[/~]", "rm -rf on root or home paths is extremely dangerous."),
    # Git stash drop/clear
    (
        r"git\s+stash\s+drop",
        "git stash drop permanently deletes stashed changes. List stashes first.",
    ),
    (r"git\s+stash\s+clear", "git stash clear permanently deletes ALL stashed changes."),
    # Git history rewriting
    (r"git\s+filter-branch", "git filter-branch rewrites history destructively."),
    (r"git\s+reflog\s+expire", "git reflog expire destroys recovery points permanently."),
    (r"git\s+reflog\s+delete", "git reflog delete removes recovery points permanently."),
    (r"git\s+rebase\s+-i", "Interactive rebase requires user input and can lose commits."),
    (r"git\s+rebase\s+--root", "Rebasing from root rewrites entire repository history."),
    (
        r"git\s+commit\s+.*--amend",
        "git commit --amend rewrites the last commit. Can cause issues if already pushed.",
    ),
    (
        r"git\s+gc\s+.*--prune=now",
        "git gc --prune=now aggressively removes objects, destroying recovery ability.",
    ),
    (
        r"git\s+prune\b",
        "git prune removes unreachable objects. Usually run via gc, direct use is risky.",
    ),
    (
        r"git\s+worktree\s+remove\s+.*--force",
        "git worktree remove --force can lose uncommitted changes in worktree.",
    ),
    # File truncation
    (r":\s*>\s*\S", "Colon-redirect (: > file) truncates file to zero bytes."),
    (
        r">\s*\.(env|gitignore|claude|bashrc|zshrc|profile)",
        "Redirect to dotfile can destroy configuration. Verify target.",
    ),
    # Bulk deletion
    (r"find\s+.*-delete", "find -delete removes files without confirmation. Use -print first."),
    (r"\|\s*xargs\s+.*rm", "Piped rm can delete unexpected files. Review with echo first."),
    # Permissions
    (r"chmod\s+-R\s+000", "chmod -R 000 removes all permissions recursively."),
    (r"chown\s+-R\s+", "chown -R changes ownership recursively. Can break system access."),
    # File truncation
    (r"truncate\s+", "truncate can destroy file contents. Verify this is intended."),
    (r"cat\s+/dev/null\s*>\s*", "Redirecting /dev/null truncates file to zero bytes."),
    # rsync delete
    (r"rsync\s+.*--delete", "rsync --delete removes files at destination not in source."),
    # Database destruction
    (r"drop\s+database", "DROP DATABASE destroys entire database. Verify this is intended."),
    (r"drop\s+table", "DROP TABLE destroys table and all data. Verify this is intended."),
    (
        r"truncate\s+table",
        "TRUNCATE TABLE deletes all rows without logging. Use DELETE for safety.",
    ),
    # Docker cleanup
    (r"docker\s+system\s+prune\s+-a", "docker system prune -a removes all unused images."),
    (
        r"docker\s+volume\s+prune",
        "docker volume prune removes unused volumes which may contain data.",
    ),
]

# Safe patterns - allowlist (checked first)
SAFE_PATTERNS = [
    r"git\s+checkout\s+-b\s+",  # Creating new branch
    r"git\s+checkout\s+--orphan\s+",  # Creating orphan branch
    r"git\s+restore\s+--staged\s+",  # Unstaging (safe)
    r"git\s+clean\s+-n",  # Dry run
    r"git\s+clean\s+--dry-run",  # Dry run
    # Allow rm -rf on temp directories
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+/tmp/",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+/var/tmp/",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+\$TMPDIR/",
    # Allow --force-with-lease
    r"git\s+push\s+.*--force-with-lease",
    # Allow find -delete on temp/cache
    r"find\s+/tmp.*-delete",
    r"find\s+.*__pycache__.*-delete",
    r"find\s+.*\.pytest_cache.*-delete",
    r"find\s+.*node_modules.*-delete",
    # Safe rsync --delete to build/cache
    r"rsync\s+.*--delete.*node_modules",
    r"rsync\s+.*--delete.*/tmp/",
    r"rsync\s+.*--delete.*__pycache__",
    r"rsync\s+.*--delete.*\.cache",
    r"rsync\s+.*--delete.*dist/?",
    r"rsync\s+.*--delete.*build/?",
    # Allow rm -rf on development artifacts
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+node_modules",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+\.?dist/?",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+\.?build/?",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+__pycache__",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+\.pytest_cache",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+\.venv/?",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+venv/?",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+\.cache/?",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+coverage/?",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+\.coverage",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+htmlcov/?",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+\.next/?",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+\.nuxt/?",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+target/?",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+\.mypy_cache/?",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+\.ruff_cache/?",
    r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+\.hypothesis/?",
    # Safe truncate for logs
    r"truncate\s+.*\.log\b",
    r"truncate\s+.*/tmp/",
    # Docker with --dry-run
    r"docker\s+.*--dry-run",
]


def check(ctx: dict) -> dict | None:
    """Block destructive git/filesystem commands.

    Args:
        ctx: Hook context with tool_name, tool_input

    Returns:
        None if allowed, {"decision": "block", "reason": str} if blocked
    """
    tool_name = ctx.get("tool_name", "")
    if tool_name != "Bash":
        return None

    tool_input = ctx.get("tool_input", {})
    command = tool_input.get("command", "")

    if not command:
        return None

    # Check safe patterns first (allowlist)
    for pattern in SAFE_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return None

    # Check destructive patterns
    for pattern, reason in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return {
                "decision": "block",
                "reason": (
                    f"BLOCKED by git_safety guard\n\n"
                    f"Reason: {reason}\n\n"
                    f"Command: {command}\n\n"
                    f"If this operation is truly needed, ask the user for explicit "
                    f"permission and have them run the command manually."
                ),
            }

    return None
