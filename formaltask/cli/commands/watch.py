"""Watch command - monitor workers, optionally spawn new tasks.

antirez-style: one command, simple default.
- Default: just watch (status display)
- With --spawn: auto-spawn new ready tasks
- With --cleanup: kill orphaned sessions (completed + PR merged)

Note: Does NOT auto-restart orphaned workers. Use ft work restart for that.
"""

import logging
import os
import time
from datetime import datetime

from formaltask import cmux
from formaltask.cli.context import with_db_path
from formaltask.core.rules_builtin import ORCHESTRATION_RULES
from formaltask.paths import get_claude_home
from formaltask.tasks.spawnability import get_spawnable_tasks
from formaltask.workers.crash_detector import get_orphaned_workers
from formaltask.workers.orchestrator import (
    DB_ERROR,
    auto_spawn_cycle,
    count_running_workers,
)

logger = logging.getLogger(__name__)

# ANSI colors
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
DIM = "\033[2m"
NC = "\033[0m"

# Default max workers
DEFAULT_MAX_WORKERS = 5


def _print_status_block(
    db_path: str, modes: list[str], max_workers: int, interval: int, action: str | None = None
):
    """Print the status block with current worker/queue counts."""
    running = len(cmux.get_all_task_sessions())

    # Get spawnable count if in spawn mode
    queue_count = 0
    if "spawn" in modes:
        queue_count = len(get_spawnable_tasks(db_path))

    print(f"\n{CYAN}─── WATCH ───{NC}")
    if action:
        print(f"  {action}")
    print()
    print(f"  {DIM}Mode:{NC}     {' + '.join(modes)}")
    print(f"  {DIM}Workers:{NC}  {running}/{max_workers} active")
    if "spawn" in modes:
        print(f"  {DIM}Queue:{NC}    {queue_count} ready")
    print(f"  {DIM}Interval:{NC} {interval}s")
    print()


def setup_parser(subparser):
    """Configure argument parser for watch command."""
    subparser.add_argument("--db-path", default=None, help="Database path")
    subparser.add_argument(
        "--spawn",
        "-s",
        action="store_true",
        help=f"Auto-spawn ready tasks (use -n to set max workers, default: {DEFAULT_MAX_WORKERS})",
    )
    subparser.add_argument(
        "--max-workers",
        "-n",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        metavar="N",
        help=f"Max concurrent workers [default: {DEFAULT_MAX_WORKERS}]",
    )
    subparser.add_argument(
        "--cleanup",
        action="store_true",
        help="Kill orphaned sessions (completed tasks with merged PRs)",
    )
    subparser.add_argument(
        "--interval",
        type=int,
        default=10,
        metavar="SEC",
        help="Polling interval [default: 10s]",
    )
    subparser.add_argument(
        "--log-file",
        default=str(get_claude_home() / "logs" / "watch.log"),
        help="Log file path",
    )


@with_db_path
def execute(db_path: str, args) -> int:
    """Run the watch daemon."""
    interval = args.interval
    log_file = args.log_file
    spawn_enabled = args.spawn
    cleanup_enabled = args.cleanup

    # Set up file logging
    _setup_logging(log_file)

    # Prompt for max workers if spawn mode enabled
    if spawn_enabled:
        max_workers = _prompt_max_workers(args.max_workers)
    else:
        max_workers = args.max_workers

    # Build mode description
    modes = ["watch"]
    if spawn_enabled:
        modes.append("spawn")
    if cleanup_enabled:
        modes.append("cleanup")

    # Initial status block
    _print_status_block(db_path, modes, max_workers, interval)

    logger.info(
        "Watch starting (spawn=%s, cleanup=%s, max_workers=%d, interval=%ds)",
        spawn_enabled,
        cleanup_enabled,
        max_workers,
        interval,
    )

    try:
        while True:
            _daemon_cycle(db_path, max_workers, spawn_enabled, modes, interval)
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Watch stopped by user")
        print(f"\n{CYAN}Stopped.{NC}")
        return 0


def _setup_logging(log_file: str):
    """Configure file logging for watch daemon."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    handler = logging.FileHandler(log_file)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _prompt_max_workers(default: int) -> int:
    """Prompt user for max parallel workers."""
    try:
        user_input = input(f"Max parallel workers [{default}]: ").strip()
        if not user_input:
            return default
        value = int(user_input)
        if value < 1:
            print(f"{YELLOW}Invalid, using default {default}{NC}")
            return default
        return value
    except ValueError:
        print(f"{YELLOW}Invalid, using default {default}{NC}")
        return default
    except (EOFError, KeyboardInterrupt):
        print()
        return default


def _daemon_cycle(db_path, max_workers, spawn_enabled, modes, interval):
    """Execute one daemon cycle: optionally spawn new tasks.

    Note: Does NOT auto-restart orphaned workers. Use ft work restart for that.
    """
    running = count_running_workers()
    if running == DB_ERROR:
        print(f"\r{RED}⚠{NC} DB error", end="", flush=True)
        return

    timestamp = datetime.now().strftime("%H:%M:%S")

    # Check for orphaned workers (crashed or killed)
    orphaned = get_orphaned_workers(db_path=db_path)
    orphaned_str = f"  {RED}⚠ {len(orphaned)} orphaned{NC}" if orphaned else ""

    # Watch-only mode: rules + supervisor but no spawning
    if not spawn_enabled:
        auto_spawn_cycle(
            db_path,
            0,
            orchestration_rules=ORCHESTRATION_RULES,
            check_supervisor=True,
        )
        print(
            f"\r  Watching...  {YELLOW}{running}{NC} active{orphaned_str}  {DIM}{timestamp}{NC}    ",
            end="",
            flush=True,
        )
        return

    # Spawn mode: delegate to orchestrator (handles transition, error recovery, rules, supervisor)
    spawned = auto_spawn_cycle(
        db_path,
        max_workers,
        orchestration_rules=ORCHESTRATION_RULES,
        check_supervisor=True,
    )

    if spawned:
        actions = [f"{GREEN}▶{NC} #{tid}" for tid in spawned]
        _print_status_block(db_path, modes, max_workers, interval, " | ".join(actions))
    else:
        spawnable_count = len(get_spawnable_tasks(db_path))
        queue_info = f"  {DIM}queue: {spawnable_count}{NC}" if spawnable_count else ""
        workers_str = f"{running} (max {max_workers})"
        print(
            f"\r  Watching...  {YELLOW}{workers_str}{NC}{queue_info}{orphaned_str}  {DIM}{timestamp}{NC}    ",
            end="",
            flush=True,
        )
