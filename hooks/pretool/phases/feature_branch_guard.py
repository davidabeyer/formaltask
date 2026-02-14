"""Feature branch guard phase - enforces correct branch targeting.

Blocks:
- gh pr create without correct --base flag when .task/target_branch specifies a feature branch
- git rebase targeting origin/master when .task/target_branch specifies a feature branch
"""

import re
from pathlib import Path

# Default branches that don't require special targeting
DEFAULT_BRANCHES = {"master", "main"}


def _get_target_branch(cwd: Path) -> str | None:
    """Read target branch from .task/target_branch file."""
    target_file = cwd / ".task" / "target_branch"
    if target_file.exists():
        try:
            return target_file.read_text().strip()
        except OSError:
            return None
    return None


def _extract_base_flag(command: str) -> str | None:
    """Extract --base value from gh pr create command."""
    match = re.search(r"--base[=\s]+([^\s]+)", command)
    if match:
        return match.group(1).strip("\"'")
    return None


def _extract_rebase_target(command: str) -> str | None:
    """Extract rebase target branch from git rebase command."""
    match = re.search(
        r"git\s+rebase\s+(?:(?:-[a-zA-Z]+|--[a-zA-Z-]+(?:[=\s][^\s]+)?)\s+)*origin/([^\s]+)",
        command,
    )
    if match:
        return match.group(1)
    return None


def check(ctx: dict) -> dict | None:
    """Validate branch targeting for feature branches.

    Returns:
        None to allow, or {"decision": "block", "reason": str} to block.
    """
    if ctx.get("tool_name") != "Bash":
        return None

    command = ctx.get("tool_input", {}).get("command", "")
    cwd = Path(ctx.get("cwd", "."))
    target_branch = _get_target_branch(cwd)

    # No target branch file - allow all
    if not target_branch:
        return None

    # Target is master/main - no special enforcement needed
    if target_branch in DEFAULT_BRANCHES:
        return None

    # Check gh pr create
    if "gh pr create" in command:
        base = _extract_base_flag(command)
        if base != target_branch:
            return {
                "decision": "block",
                "reason": (
                    f"BLOCKED: gh pr create must target feature branch.\n\n"
                    f"Expected: --base {target_branch}\n"
                    f"Got: --base {base or '(not specified)'}\n\n"
                    f"This task targets '{target_branch}', not master/main.\n"
                    f"Use: gh pr create --base {target_branch} ..."
                ),
            }

    # Check git rebase
    if "git rebase" in command:
        rebase_target = _extract_rebase_target(command)
        if rebase_target and rebase_target in DEFAULT_BRANCHES:
            return {
                "decision": "block",
                "reason": (
                    f"BLOCKED: git rebase should target feature branch.\n\n"
                    f"Expected: origin/{target_branch}\n"
                    f"Got: origin/{rebase_target}\n\n"
                    f"This task targets '{target_branch}', not {rebase_target}.\n"
                    f"Use: git rebase origin/{target_branch}"
                ),
            }

    return None
