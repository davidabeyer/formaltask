"""WebFetch GitHub URL redirect phase.

Redirects GitHub URLs to GitChamber for AI-optimized access.
Code files get showLineNumbers=true parameter.
"""

from __future__ import annotations

import re

# File extensions that benefit from line numbers
CODE_EXTENSIONS = {".js", ".ts", ".py", ".go", ".rs", ".java", ".c", ".cpp"}


def transform_github_url(url: str) -> str | None:
    """Transform GitHub URLs to GitChamber equivalents.

    Args:
        url: The URL to potentially transform

    Returns:
        GitChamber URL if GitHub URL, None otherwise
    """
    # Pattern: raw.githubusercontent.com/owner/repo/branch/path
    raw_match = re.match(
        r"https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)",
        url,
    )
    if raw_match:
        owner, repo, branch, path = raw_match.groups()
        base = f"https://gitchamber.com/repos/{owner}/{repo}/{branch}/files/{path}"
        if any(path.endswith(ext) for ext in CODE_EXTENSIONS):
            return f"{base}?showLineNumbers=true"
        return base

    # Pattern: github.com/owner/repo/blob/branch/path
    blob_match = re.match(
        r"https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)",
        url,
    )
    if blob_match:
        owner, repo, branch, path = blob_match.groups()
        base = f"https://gitchamber.com/repos/{owner}/{repo}/{branch}/files/{path}"
        if any(path.endswith(ext) for ext in CODE_EXTENSIONS):
            return f"{base}?showLineNumbers=true"
        return base

    return None


def check(ctx: dict) -> dict | None:
    """Redirect GitHub URLs to GitChamber for AI-optimized access.

    Args:
        ctx: Context dict with tool_name, tool_input fields

    Returns:
        Dict with updatedInput to modify the URL, None otherwise.
    """
    tool_name = ctx.get("tool_name", "")
    if tool_name != "WebFetch":
        return None

    tool_input = ctx.get("tool_input", {})
    url = tool_input.get("url", "")

    new_url = transform_github_url(url)
    if not new_url:
        return None

    # Modify the URL input to use GitChamber
    return {
        "updatedInput": {"url": new_url},
        "additionalContext": f"GitChamber redirect: {url[:50]}... → {new_url[:50]}...",
    }
