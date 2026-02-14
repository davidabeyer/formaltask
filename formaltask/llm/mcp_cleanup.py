"""MCP orphan cleanup library.

Task #2457: Provides a callable function to clean up orphaned MCP server processes.
Extracted from tools/mcp-cleanup.py for programmatic use.

Orphaned MCPs are those whose parent chain leads to PID 1 (init/launchd)
without passing through any Claude process.
"""

import contextlib
import logging
import os
import signal
import subprocess

log = logging.getLogger(__name__)

# MCP process identification patterns (conservative - only match clear MCP processes)
MCP_PATTERNS = [
    r"auggie.*--mcp",
    r"context7-mcp",
    r"exa-mcp-server",
    r"morph-mcp",
    r"morphmcp",
    r"tmux-mcp",
    r"dcl_wrapper\.py",
    r"@upstash/context7-mcp",
    r"@morphllm/morphmcp",
]


def _get_claude_pids() -> set[int]:
    """Get all running Claude process PIDs."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "claude"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return {int(pid) for pid in result.stdout.strip().split() if pid}
    except Exception as e:
        log.debug("Failed to get Claude PIDs: %s", e)
        return set()


def _get_ppid(pid: int) -> int | None:
    """Get parent PID of a process. Returns None if process doesn't exist."""
    try:
        result = subprocess.run(
            ["ps", "-o", "ppid=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        ppid_str = result.stdout.strip()
        return int(ppid_str) if ppid_str else None
    except Exception as e:
        log.debug("Failed to get PPID for PID %d: %s", pid, e)
        return None


def _is_orphaned(pid: int, claude_pids: set[int]) -> bool:
    """Check if a process is orphaned (no Claude ancestor).

    Returns True if the process's parent chain leads to PID 1 (init)
    without passing through any Claude process.
    """
    visited: set[int] = set()
    current = pid
    max_depth = 50

    for _ in range(max_depth):
        if current in visited:
            return True
        visited.add(current)

        if current in claude_pids:
            return False

        ppid = _get_ppid(current)
        if ppid is None or ppid <= 1 or ppid == current:
            return True
        current = ppid

    return True


def _find_mcp_processes() -> set[int]:
    """Find all processes matching MCP patterns."""
    mcp_pids: set[int] = set()

    for pattern in MCP_PATTERNS:
        try:
            result = subprocess.run(
                ["pgrep", "-f", pattern],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for pid_str in result.stdout.strip().split():
                if pid_str:
                    with contextlib.suppress(ValueError):
                        mcp_pids.add(int(pid_str))
        except Exception as e:
            log.debug("Failed to search for pattern %r: %s", pattern, e)

    mcp_pids.discard(os.getpid())
    return mcp_pids


def cleanup_orphan_mcps() -> int:
    """Kill orphaned MCP processes.

    Returns:
        Number of processes killed.

    This function identifies MCP processes whose parent chain leads to
    PID 1 (init/launchd) without passing through any Claude process,
    and terminates them with SIGTERM.
    """
    claude_pids = _get_claude_pids()
    mcp_pids = _find_mcp_processes()
    killed = 0

    for pid in mcp_pids:
        if _is_orphaned(pid, claude_pids):
            try:
                os.kill(pid, signal.SIGTERM)
                log.debug("Killed orphaned MCP process %d", pid)
                killed += 1
            except ProcessLookupError:
                pass  # Already gone
            except PermissionError:
                log.debug("Permission denied killing PID %d", pid)
            except OSError as e:
                log.debug("Error killing PID %d: %s", pid, e)

    if killed:
        log.info("Cleaned up %d orphaned MCP process(es)", killed)

    return killed
