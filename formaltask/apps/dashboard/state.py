"""Worker state fetching with parallel execution."""

from __future__ import annotations

import logging
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path

# Patterns for trimming statusline
_DIVIDER = re.compile(r"[─━]{10,}")
# Claude Code UI has right border (│▐) - truncate line at first occurrence
# The bar appears mid-line when terminal width causes wrapped display
_BOX_BORDER = re.compile(r"[│▐].*$")


def trim_statusline(output: str) -> str:
    """Remove Claude Code statusline from captured output.

    Returns original output if detection fails (defensive fallback).
    Preserves trailing newline if present in original.

    Statusline has TWO dividers - we find the FIRST by searching backwards
    and continuing to search after finding one.
    """
    if not output:
        return ""

    had_trailing_newline = output.endswith("\n")
    lines = output.splitlines()

    if len(lines) < 5:
        return output

    # Search only the last 10 lines for dividers
    search_start = max(0, len(lines) - 10)
    cut_index = None

    for i in range(len(lines) - 1, search_start - 1, -1):
        if _DIVIDER.search(lines[i]):
            cut_index = i

    if cut_index is not None:
        content_lines = lines[:cut_index]
    else:
        content_lines = lines

    # Truncate lines at box-drawing border characters (│▐)
    # Claude Code UI borders appear mid-line when terminal width wraps
    cleaned_lines = [_BOX_BORDER.sub("", line) for line in content_lines]

    result = "\n".join(cleaned_lines)
    if had_trailing_newline and result:
        result += "\n"
    return result


from formaltask.git.github import get_prs_for_tasks
from formaltask.state.findings import get_findings_with_disposition
from formaltask.workers.health import (
    _fetch_task_metadata_batch,
    get_worker_state_dict,
)

log = logging.getLogger(__name__)


def fetch_worker_states(
    sessions: list[tuple[str, int]],
    db_path: Path | None,
    skip_pr_fetch: bool = False,
) -> list[dict]:
    """Fetch worker states in parallel (up to 8 workers, 10s timeout)."""
    if not sessions:
        return []

    task_ids = [task_id for _, task_id in sessions]
    metadata_cache = _fetch_task_metadata_batch(task_ids, str(db_path)) if db_path else {}

    if not skip_pr_fetch:
        get_prs_for_tasks(task_ids)

    results: list[dict] = []
    max_workers = min(len(sessions), 8)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                get_worker_state_dict,
                task_id,
                session_name,
                db_path=str(db_path) if db_path else None,
                metadata_cache=metadata_cache,
            ): session_name
            for session_name, task_id in sessions
        }

        done, pending = wait(futures, timeout=10)

        for future in done:
            session_name = futures[future]
            try:
                state = future.result()
                state["lines"] = trim_statusline(state.get("pane_output") or "")
                results.append(state)
            except OSError as e:
                log.warning("Failed to fetch state for %s: %s", session_name, e)

        for future in pending:
            log.warning("Timeout fetching state for %s", futures[future])

    if db_path:
        for state in results:
            task_id = state.get("task_id")
            if task_id:
                try:
                    state["cached_findings"] = get_findings_with_disposition(task_id, str(db_path))
                except (sqlite3.Error, OSError) as e:
                    log.debug("Failed to fetch findings for task %d: %s", task_id, e)
                    state["cached_findings"] = []

    return results
