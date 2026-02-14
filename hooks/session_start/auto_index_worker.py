#!/usr/bin/env python3
"""
Auto-index background worker for SessionStart hook.

Performs the actual reindexing work in a detached background process.
Called by spawn_worker() from auto_index_codebase.py.

Implements <!-- BACKGROUND-WORKERS --> from CLAUDE.md.
"""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import asyncio
import logging
import os
from pathlib import Path

# MCP SDK imports (optional - used at runtime when MCP SDK is installed)
from mcp import ClientSession, StdioServerParameters  # type: ignore[import-not-found]
from mcp.client.stdio import stdio_client  # type: ignore[import-not-found]

from formaltask.paths import get_project_root, get_workflow_worker_logs_dir

# Import from parent module for shared constants
from hooks.session_start.auto_index_codebase import (
    STATE_DIR,
    load_claude_context_env,
    update_last_index_time,
)

# Setup logging (Task #2483: use path_config for configurability)
LOG_DIR = get_workflow_worker_logs_dir()
LOG_FILE = LOG_DIR / "auto-index.log"


def setup_logging() -> logging.Logger:
    """Configure logging for the worker."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("auto-index-worker")
    logger.setLevel(logging.INFO)

    # Avoid adding duplicate handlers
    if not logger.handlers:
        handler = logging.FileHandler(LOG_FILE)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(handler)

    return logger


async def async_call_index_codebase(
    codebase_path: str | None = None, logger: logging.Logger | None = None
) -> bool:
    """Call claude-context index_codebase via MCP Python SDK.

    Uses the verified MCP SDK pattern from the proposal critique.
    Environment variables are loaded from ~/.claude.json.

    Returns True on success, False on failure.
    """
    if logger is None:
        logger = setup_logging()

    if codebase_path is None:
        codebase_path = str(get_project_root())

    # Load environment from ~/.claude.json
    env = load_claude_context_env()

    # Merge with system PATH
    full_env = {**os.environ, **env}

    server_params = StdioServerParameters(
        command="npx", args=["@zilliz/claude-context-mcp@latest"], env=full_env
    )

    try:
        logger.info("Connecting to claude-context MCP server...")
        async with (
            stdio_client(server_params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            logger.info("MCP session initialized, calling index_codebase...")

            result = await session.call_tool(
                "index_codebase",
                arguments={
                    "path": codebase_path,
                    "force": False,  # Incremental - only re-index changed files
                },
            )

            logger.info(f"index_codebase result: {result}")

            # Check if MCP returned an error
            if result.isError:
                # "Already indexed" with force=false is actually success (no changes needed)
                error_text = str(result.content[0].text) if result.content else ""
                if "already indexed" in error_text.lower():
                    logger.info("Index is current, no changes needed")
                    return True
                logger.warning("MCP returned error, will retry next interval")
                return False

            return True

    except Exception as e:
        logger.error(f"MCP call failed: {type(e).__name__}: {e}")
        return False


def call_index_codebase() -> bool:
    """Synchronous wrapper for async MCP call."""
    return asyncio.run(async_call_index_codebase())


def run_reindex() -> None:
    """Main reindex function with lock cleanup.

    CRITICAL: Lock file is cleaned up in finally block to ensure
    it's removed on both success AND failure.
    """
    lock_file = STATE_DIR / "reindex.lock"
    logger = setup_logging()

    try:
        logger.info("Starting reindex worker")
        success = call_index_codebase()
        if success:
            logger.info("Reindex completed successfully")
            update_last_index_time()  # Track successful index time
        else:
            logger.error("Reindex failed")
    except Exception as e:
        logger.error(f"Reindex error: {type(e).__name__}: {e}")
    finally:
        # ALWAYS clean up lock file
        lock_file.unlink(missing_ok=True)
        logger.info("Lock file cleaned up")


def main() -> None:
    """Entry point for background worker."""
    run_reindex()


if __name__ == "__main__":
    main()
