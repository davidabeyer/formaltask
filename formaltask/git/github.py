"""Batch GitHub PR query with 300s TTL cache."""

import json
import logging
import subprocess
import time
from dataclasses import dataclass
from typing import Literal

from formaltask.utils.subprocess import build_subprocess_env

logger = logging.getLogger(__name__)

_pr_cache: tuple[dict[int, "PRInfo"], float] | None = None
_cache_ttl: float = 300.0


@dataclass
class PRInfo:
    """PR info: number, state (OPEN/CLOSED/MERGED), merged bool."""

    number: int
    state: Literal["OPEN", "CLOSED", "MERGED"]
    merged: bool


def get_prs_for_tasks(task_ids: list[int] | None = None) -> dict[int, PRInfo]:  # noqa: C901
    """Get PRs for tasks. Fail-open: returns {} on any GitHub error."""
    global _pr_cache

    if _pr_cache is not None:
        cached_result, cached_time = _pr_cache
        if time.time() - cached_time < _cache_ttl:
            return cached_result

    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "all",
                "--json",
                "number,headRefName,state,mergedAt",
                "--limit",
                "200",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env=build_subprocess_env(extra_whitelist=["GH_TOKEN", "GITHUB_TOKEN"]),
        )
    except subprocess.TimeoutExpired:
        logger.warning("GitHub PR query timed out after 30s")
        return {}
    except FileNotFoundError:
        logger.warning("gh CLI not found")
        return {}
    if result.returncode != 0:
        return {}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON response from gh pr list")
        return {}
    prs: dict[int, PRInfo] = {}
    task_id_set = set(task_ids) if task_ids else None
    for pr in data:
        branch = pr.get("headRefName", "")
        if branch.startswith("task-"):
            task_id_str = branch[5:]
            if task_id_str.isdigit():
                task_id = int(task_id_str)
                if task_id_set is not None and task_id not in task_id_set:
                    continue
                merged = pr.get("mergedAt") is not None
                raw_state = pr.get("state")
                if not merged and raw_state is None:
                    continue
                state = "MERGED" if merged else raw_state
                try:
                    prs[task_id] = PRInfo(number=pr["number"], state=state, merged=merged)
                except KeyError:
                    continue
    _pr_cache = (prs, time.time())
    return prs


def get_pr_for_task(task_id: int) -> PRInfo | None:
    """Get PR for a single task."""
    return get_prs_for_tasks().get(task_id)
