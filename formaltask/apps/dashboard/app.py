"""Dashboard application module - WorkerDashboard and supporting classes."""

import asyncio
import logging
import os
import shlex
import subprocess
import sys
import termios
import time
from pathlib import Path

from rich.markup import escape
from textual import on, work
from textual.app import App, ComposeResult, ScreenStackError, SuspendNotSupported
from textual.notifications import SeverityLevel
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Footer
from textual.worker import get_current_worker

from formaltask.core.rules_builtin import ORCHESTRATION_RULES
from formaltask.llm.mcp_cleanup import cleanup_orphan_mcps
from formaltask.paths import get_claude_home, task_worktree
from formaltask.tasks.lifecycle import InvalidTransitionError, transition_task_status
from formaltask.tasks.spawnability import get_spawnable_tasks_with_titles
from formaltask.tmux import (
    attach_session,
    capture_pane,
    create_session,
    get_all_task_sessions,
    is_pane_dead,
    kill_session,
    send_keys,
    session_exists,
)
from formaltask.workers.inbox import get_blocked_workers
from formaltask.workers.orchestrator import DB_ERROR, auto_spawn_cycle, count_running_workers
from formaltask.workers.spawner import SpawnError, spawn_worker

from .state import fetch_worker_states, trim_statusline
from .widgets import StatusBar, TaskList, TerminalPane

log = logging.getLogger(__name__)

CSS_PATH = Path(__file__).parent / "theme.tcss"

# Spawn animation: cycling dot characters
SPAWN_DOTS = ["", ".", "..", "...", "....", "....."]
SPAWN_TIMEOUT_SECONDS = 60.0


# Domain messages
class WorkerStatesUpdated(Message):
    def __init__(
        self,
        states: dict[int, dict],
        spawnable_tasks: list[dict] | None = None,
        blocked_workers: list[dict] | None = None,
        captured_terminal_content: str | None = None,
    ) -> None:
        self.states = states
        self.spawnable_tasks = spawnable_tasks if spawnable_tasks is not None else []
        self.blocked_workers = blocked_workers if blocked_workers is not None else []
        self.captured_terminal_content = captured_terminal_content
        super().__init__()


class WorkerStateChanged(Message):
    def __init__(self, task_id: int, from_state: str, to_state: str, worker: dict) -> None:
        self.task_id = task_id
        self.from_state = from_state
        self.to_state = to_state
        self.worker = worker
        super().__init__()


class WorkerKilled(Message):
    def __init__(self, task_id: int, next_task_id: int | None) -> None:
        self.task_id = task_id
        self.next_task_id = next_task_id
        super().__init__()


class TaskSpawned(Message):
    def __init__(self, task_id: int) -> None:
        self.task_id = task_id
        super().__init__()


class SpawnFailed(Message):
    def __init__(self, task_id: int, error: str) -> None:
        self.task_id = task_id
        self.error = error
        super().__init__()


class AutoSpawnActivity(Message):
    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__()


POLL_INTERVAL: float = 0.4


def _parse_session_tuples(sessions: list[str]) -> list[tuple[str, int]]:
    """Convert session names to (session_name, task_id) tuples."""
    tuples: list[tuple[str, int]] = []
    for name in sessions:
        if name.startswith("task-"):
            try:
                task_id = int(name.replace("task-", ""))
                tuples.append((name, task_id))
            except ValueError:
                continue
    return tuples


class WorkerDashboard(App):
    """TUI dashboard for FormalTask parallel workers."""

    TITLE = "FormalTask Dashboard"
    SUB_TITLE = ""
    ENABLE_COMMAND_PALETTE = False

    CSS_PATH = CSS_PATH
    AUTO_SPAWN_INTERVAL: float = 10.0
    _MAX_WORKERS_MIN: int = 1
    _MAX_WORKERS_MAX: int = 10

    selected_task_id: reactive[int | None] = reactive(None, repaint=False)
    auto_spawn_enabled: reactive[bool] = reactive(False)
    max_workers: reactive[int] = reactive(5)

    BINDINGS = [
        Binding("j", "nav_next", "Nav", show=True, priority=True, key_display="j/k"),
        Binding("k", "nav_prev", "", show=False, priority=True),
        Binding("enter", "attach_focused", "Attach", show=True, priority=True),
        Binding("d", "dismiss_blocked", "", show=False, priority=True),
        Binding("X", "kill", "Kill", priority=True),
        Binding("S", "spawn", "Spawn", key_display="S"),
        Binding("A", "toggle_auto_spawn", "Auto", key_display="A"),
        Binding("plus", "increase_limit", "Limit", key_display="+/-", priority=True),
        Binding("equals_sign", "increase_limit", "", show=False, priority=True),
        Binding("minus", "decrease_limit", "", show=False, priority=True),
        Binding("R", "restart", "Restart", priority=True),
        Binding("i", "toggle_inbox", "Inbox", key_display="i"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, db_path: "Path | None" = None) -> None:
        super().__init__()
        self.db_path = db_path
        self._prev_health_states: dict[int, str] = {}
        self._worker_states: list[dict] = []
        self._spawnable_tasks: list[dict] = []
        self._blocked_workers: list[dict] = []
        self._pending_kill: tuple[int, float] | None = None
        self._pending_restart: tuple[int, float] | None = None
        self._spawning_tasks: dict[int, float] = {}

    @property
    def _modal_active(self) -> bool:
        """True when a modal screen (e.g. InboxScreen) is on top."""
        from textual.screen import ModalScreen

        try:
            return isinstance(self.screen, ModalScreen)
        except Exception:
            return False

    @property
    def sidebar(self) -> TaskList:
        return self.query_one("#task-list", TaskList)

    def compose(self) -> ComposeResult:
        yield StatusBar(id="status-bar")
        yield TaskList(id="task-list")
        yield TerminalPane(id="terminal-pane")
        yield Footer()

    def notify(
        self,
        message: str,
        *,
        title: str = "",
        severity: SeverityLevel = "information",
        timeout: float | None = None,
        markup: bool = True,
    ) -> None:
        """Route notifications to the status bar flash instead of Toast."""
        try:
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.flash(message, title=title, severity=severity, timeout=timeout or 3.0)
        except NoMatches:
            super().notify(message, title=title, severity=severity, timeout=timeout, markup=markup)

    def on_mount(self) -> None:
        self.poll_workers()

    def watch_selected_task_id(self, task_id: int | None) -> None:
        try:
            sidebar = self.query_one("#task-list", TaskList)
            sidebar.update_selection(task_id)
        except (NoMatches, ScreenStackError):
            pass
        try:
            pane = self.query_one("#terminal-pane", TerminalPane)
            pane.update_content(task_id=task_id, captured_content=None)
        except (NoMatches, ScreenStackError):
            pass

    @work(exclusive=True, thread=True)
    def poll_workers(self) -> None:
        """Background polling for worker states."""
        worker = get_current_worker()
        base_interval = POLL_INTERVAL
        max_interval = 60.0
        consecutive_errors = 0

        while not worker.is_cancelled:
            try:
                sessions = get_all_task_sessions()
                session_tuples = _parse_session_tuples(sessions)
                states = fetch_worker_states(session_tuples, self.db_path)
                self._worker_states = states

                states_dict: dict[int, dict] = {}
                for state in states:
                    task_id = state.get("task_id")
                    if task_id is None:
                        continue
                    states_dict[task_id] = state
                    new_state = state.get("health_state", "unknown")
                    old_state = self._prev_health_states.get(task_id, "unknown")
                    if old_state != new_state:
                        self.post_message(
                            WorkerStateChanged(
                                task_id=task_id,
                                from_state=old_state,
                                to_state=new_state,
                                worker=state,
                            )
                        )
                    self._prev_health_states[task_id] = new_state

                current_task_ids = set(states_dict.keys())
                for stale_id in set(self._prev_health_states.keys()) - current_task_ids:
                    del self._prev_health_states[stale_id]

                # Clean up _spawning_tasks: remove if tmux detected or timed out
                now = time.time()
                for tid in list(self._spawning_tasks):
                    if (
                        tid in states_dict
                        or (now - self._spawning_tasks[tid]) > SPAWN_TIMEOUT_SECONDS
                    ):
                        del self._spawning_tasks[tid]

                spawnable_tasks = (
                    get_spawnable_tasks_with_titles(str(self.db_path)) if self.db_path else []
                )
                blocked_workers = get_blocked_workers(str(self.db_path)) if self.db_path else []

                # Capture selected worker's terminal in background thread
                captured_terminal_content = None
                selected_id = self.selected_task_id
                if selected_id is not None:
                    raw = capture_pane(f"task-{selected_id}", lines=50)
                    captured_terminal_content = trim_statusline(raw) if raw is not None else ""

                self.post_message(
                    WorkerStatesUpdated(
                        states_dict,
                        spawnable_tasks=spawnable_tasks,
                        blocked_workers=blocked_workers,
                        captured_terminal_content=captured_terminal_content,
                    )
                )
                consecutive_errors = 0
                sleep_seconds = POLL_INTERVAL

            except OSError as e:
                log.error("Error polling workers: %s", e)
                consecutive_errors += 1
                sleep_seconds = min(base_interval * (2**consecutive_errors), max_interval)

            increments = int(sleep_seconds * 10)
            for _ in range(increments):
                if worker.is_cancelled:
                    return
                time.sleep(0.1)

    def action_refresh(self) -> None:
        auto_spawn_was_enabled = self.auto_spawn_enabled
        self.workers.cancel_all()
        self.poll_workers()
        if auto_spawn_was_enabled:
            self._auto_spawn_orchestrated()

    def action_attach(self) -> None:
        task_id = self.selected_task_id
        if task_id is None:
            self.notify("Select a worker first", title="No Selection", severity="error")
            return

        session_name = f"task-{task_id}"

        if not session_exists(session_name):
            self.notify(f"No tmux session for task-{task_id}", title="Not Found", severity="error")
            return

        if is_pane_dead(session_name):
            self.notify("Worker exited. Kill (X) or restart (R).", title="Dead Session", severity="warning")
            return

        if os.environ.get("TMUX"):
            self.notify("Detach from current tmux first", title="Nested tmux", severity="warning")

        # Bind F12 as detach key before attaching
        subprocess.run(
            ["tmux", "bind", "-n", "F12", "detach-client"],
            capture_output=True,
            timeout=10,
        )

        try:
            with self.suspend():
                attach_session(session_name)
                try:
                    termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
                except (termios.error, OSError):
                    pass
        except (SuspendNotSupported, RuntimeError):
            self.exit(result=("attach", task_id))
            return

        self._on_resume()

    def _on_resume(self) -> None:
        row_cache = self.sidebar._row_cache
        selected_row = None
        if row_cache:
            for task_id, row in row_cache.items():
                if self.selected_task_id is not None and task_id == self.selected_task_id:
                    selected_row = row
        self.refresh(repaint=True, layout=True)
        if selected_row is not None:
            selected_row.scroll_visible()
        self._do_resume_refresh()
        self.set_timer(2.0, self._do_full_poll)

    @work()
    async def _do_resume_refresh(self) -> None:
        await self._poll_workers(skip_pr_fetch=True)

    @work()
    async def _do_full_poll(self) -> None:
        await self._poll_workers(skip_pr_fetch=False)

    @on(WorkerStatesUpdated)
    async def on_worker_states_updated(self, event: WorkerStatesUpdated) -> None:
        await self._batch_ui_update(
            list(event.states.values()),
            spawnable_tasks=event.spawnable_tasks,
            blocked_workers=event.blocked_workers,
        )
        try:
            pane = self.query_one("#terminal-pane", TerminalPane)
            pane.update_content(
                task_id=self.selected_task_id,
                captured_content=event.captured_terminal_content,
                blocked_count=len(event.blocked_workers),
            )
        except NoMatches:
            pass

    @on(WorkerStateChanged)
    def on_worker_state_changed(self, event: WorkerStateChanged) -> None:
        if event.to_state == "error":
            task_title = event.worker.get("task_title", "Unknown")
            log.warning("Worker task-%d entered error state: %s", event.task_id, task_title)
            self.notify(
                f"[bold]task-{event.task_id}[/] {escape(task_title)}",
                title="Worker Error",
                severity="error",
            )

    @on(WorkerKilled)
    def on_worker_killed(self, event: WorkerKilled) -> None:
        self.sidebar.kill_task(event.task_id)
        self.notify(f"Worker [bold]task-{event.task_id}[/] terminated", title="Killed")
        self.selected_task_id = event.next_task_id
        self.action_refresh()

    async def _batch_ui_update(
        self,
        states: list[dict],
        spawnable_tasks: list[dict] | None = None,
        blocked_workers: list[dict] | None = None,
    ) -> None:
        with self.batch_update():
            try:
                sidebar = self.query_one("#task-list", TaskList)
                states_dict = {s["task_id"]: s for s in states if s.get("task_id") is not None}

                self._spawnable_tasks = spawnable_tasks if spawnable_tasks is not None else []
                spawnable_ids = [t["id"] for t in self._spawnable_tasks]

                # Override phase to 'spawn' for tasks in _spawning_tasks
                now = time.time()
                for tid, start_time in dict(self._spawning_tasks).items():
                    if tid in states_dict:
                        states_dict[tid]["health_state"] = "spawn"
                    # Compute cycling dots
                    elapsed = now - start_time
                    dot_idx = int(elapsed / 0.5) % len(SPAWN_DOTS)
                    if tid in states_dict:
                        states_dict[tid]["spawn_dots"] = SPAWN_DOTS[dot_idx]

                sidebar.refresh_from_states(
                    states_dict, self.selected_task_id, spawnable_ids, self._spawnable_tasks
                )
                self._update_sidebar_title()

                if self.selected_task_id is None and states:
                    first_task_id = states[0].get("task_id")
                    if first_task_id is not None:
                        self.selected_task_id = first_task_id

                self._blocked_workers = blocked_workers if blocked_workers is not None else []

                # Update StatusBar with computed counts
                self._update_status_bar(states_dict)
            except NoMatches:
                pass
            except Exception as e:
                log.warning("Failed to update UI: %s", e)

    def _update_status_bar(self, states_dict: dict[int, dict]) -> None:
        try:
            status_bar = self.query_one("#status-bar", StatusBar)
            epic_names = set()
            done = 0
            running = 0
            exit_count = 0
            help_count = 0
            for state in states_dict.values():
                health = state.get("health_state", "unknown")
                epic = state.get("epic_name")
                if epic:
                    epic_names.add(epic)
                if health in ("done", "completed", "awaiting_merge"):
                    done += 1
                elif health in ("exited",):
                    exit_count += 1
                elif health in ("needs_human", "blocked"):
                    help_count += 1
                elif health not in ("unknown", "queued"):
                    running += 1
            queued = len(self._spawnable_tasks)
            change_count = 0
            try:
                change_count = self.sidebar._change_counter
            except (NoMatches, AttributeError):
                pass
            status_bar.update(
                epic_count=len(epic_names),
                done=done,
                running=running,
                exit_count=exit_count,
                help_count=help_count,
                queued=queued,
                change_count=change_count,
            )
        except NoMatches:
            pass

    @work(exclusive=True, thread=True)
    def _spawn_task(self, task_id: int) -> None:
        if self.db_path is None:
            self.post_message(SpawnFailed(task_id, "No database path configured"))
            return
        try:
            transition_task_status(self.db_path, task_id, "in_progress")
            spawn_worker(task_id, str(self.db_path))
            self.post_message(TaskSpawned(task_id))
        except InvalidTransitionError:
            self.post_message(SpawnFailed(task_id, "Task claimed by another process"))
        except SpawnError as e:
            self.post_message(SpawnFailed(task_id, str(e)))

    def action_spawn(self) -> None:
        if self._modal_active:
            return
        sidebar = self.query_one("#task-list", TaskList)
        selected = sidebar.selected_task_id
        if selected and selected in sidebar.spawnable_ids:
            task_id = selected
        elif sidebar.spawnable_ids:
            task_id = sidebar.spawnable_ids[0]
        else:
            return
        self._spawning_tasks[task_id] = time.time()
        self._spawn_task(task_id)

    @on(TaskSpawned)
    def on_task_spawned(self, event: TaskSpawned) -> None:
        self.notify(f"Worker [bold]task-{event.task_id}[/] launched", title="Spawned")

    @on(SpawnFailed)
    def on_spawn_failed(self, event: SpawnFailed) -> None:
        # Clean up spawning state on failure
        self._spawning_tasks.pop(event.task_id, None)
        self.notify(event.error, title="Spawn Failed", severity="error")

    def action_toggle_auto_spawn(self) -> None:
        self.auto_spawn_enabled = not self.auto_spawn_enabled

    def action_increase_limit(self) -> None:
        if self.max_workers >= self._MAX_WORKERS_MAX:
            self.notify(f"Already at maximum ({self._MAX_WORKERS_MAX})", severity="warning")
            return
        old = self.max_workers
        self.max_workers = old + 1
        self.notify(f"Workers: {old} \u2192 {self.max_workers}", title="Limit")

    def action_decrease_limit(self) -> None:
        if self.max_workers <= self._MAX_WORKERS_MIN:
            self.notify(f"Already at minimum ({self._MAX_WORKERS_MIN})", severity="warning")
            return
        old = self.max_workers
        self.max_workers = old - 1
        self.notify(f"Workers: {old} \u2192 {self.max_workers}", title="Limit")

    def action_toggle_inbox(self) -> None:
        if not self._blocked_workers:
            self.notify("All workers running normally", title="Inbox Empty")
            return
        from .screens.inbox import InboxScreen

        self.push_screen(InboxScreen(self._blocked_workers, str(self.db_path)))

    def _update_sidebar_title(self) -> None:
        try:
            sidebar = self.query_one("#task-list", TaskList)
            queue_count = len(sidebar.spawnable_ids)
            parts = ["Tasks"]
            if queue_count > 0:
                parts.append(f"({queue_count} queued)")
            sidebar.border_title = " ".join(parts)
        except NoMatches:
            pass

    @work(exclusive=True, thread=True, name="auto_spawn")
    def _auto_spawn_orchestrated(self) -> None:
        worker = get_current_worker()
        while not worker.is_cancelled and self.auto_spawn_enabled:
            if self.db_path is None:
                time.sleep(self.AUTO_SPAWN_INTERVAL)
                continue

            # Steady-state activity: just show "auto (N)"
            limit = self.max_workers
            self.post_message(AutoSpawnActivity(f"auto ({limit})"))

            running = count_running_workers()
            if running == DB_ERROR:
                log.warning("Skipping auto-spawn cycle: DB_ERROR from count_running_workers")
                time.sleep(self.AUTO_SPAWN_INTERVAL)
                continue

            spawned = auto_spawn_cycle(
                str(self.db_path),
                limit,
                orchestration_rules=ORCHESTRATION_RULES,
                check_supervisor=True,
            )
            for task_id in spawned:
                self._spawning_tasks[task_id] = time.time()
                self.post_message(TaskSpawned(task_id))

            time.sleep(self.AUTO_SPAWN_INTERVAL)

    def watch_auto_spawn_enabled(self, enabled: bool) -> None:
        if enabled:
            self._auto_spawn_orchestrated()
        else:
            for w in self.workers:
                if w.name == "auto_spawn":
                    w.cancel()
        if enabled:
            self.notify("Auto-spawn enabled", severity="information")
        else:
            self.notify("Auto-spawn disabled", severity="information")
            # Clear activity text when disabling
            try:
                self.query_one("#status-bar", StatusBar).set_activity("")
            except NoMatches:
                pass
        self._update_sidebar_title()

    @on(AutoSpawnActivity)
    def on_auto_spawn_activity(self, event: AutoSpawnActivity) -> None:
        try:
            self.query_one("#status-bar", StatusBar).set_activity(event.text)
        except NoMatches:
            pass

    async def _poll_workers(self, skip_pr_fetch: bool = False) -> None:
        loop = asyncio.get_running_loop()
        sessions = await loop.run_in_executor(None, get_all_task_sessions)
        session_tuples = _parse_session_tuples(sessions)
        states = await loop.run_in_executor(
            None,
            lambda: fetch_worker_states(session_tuples, self.db_path, skip_pr_fetch=skip_pr_fetch),
        )
        self._worker_states = states
        spawnable_tasks = (
            await loop.run_in_executor(
                None, lambda: get_spawnable_tasks_with_titles(str(self.db_path))
            )
            if self.db_path
            else []
        )
        blocked_workers = (
            await loop.run_in_executor(None, lambda: get_blocked_workers(str(self.db_path)))
            if self.db_path
            else []
        )
        await self._batch_ui_update(
            states, spawnable_tasks=spawnable_tasks, blocked_workers=blocked_workers
        )

    def action_kill(self) -> None:
        if self._modal_active:
            return
        task_id = self.selected_task_id
        if task_id is None:
            self.notify("Select a worker first", title="No Selection", severity="error")
            return

        now = time.time()
        if self._pending_kill is not None:
            pending_id, pending_time = self._pending_kill
            if pending_id == task_id and (now - pending_time) < 3.0:
                self._pending_kill = None
                self._handle_kill_confirm(True, task_id)
                return

        self._pending_kill = (task_id, now)
        self.notify(f"Press [bold]X[/] again within 3s to confirm", title=f"Kill task-{task_id}?", severity="warning")

    def _handle_kill_confirm(self, confirmed: bool, task_id: int) -> None:
        if not confirmed:
            return
        try:
            self.query_one("#status-bar", StatusBar).clear_flash()
        except NoMatches:
            pass
        next_task_id = None
        if self.selected_task_id == task_id:
            task_ids = self._get_task_ids_in_order()
            if task_ids:
                try:
                    current_idx = task_ids.index(task_id)
                    if current_idx < len(task_ids) - 1:
                        next_task_id = task_ids[current_idx + 1]
                    elif current_idx > 0:
                        next_task_id = task_ids[current_idx - 1]
                except ValueError:
                    pass
        self._kill_worker_blocking(task_id, next_task_id)

    @work(thread=True, exclusive=True)
    def _kill_worker_blocking(self, task_id: int, next_task_id: int | None) -> None:
        try:
            kill_session(f"task-{task_id}")
            try:
                cleanup_orphan_mcps()
            except Exception as e:
                log.debug("MCP cleanup error (non-fatal): %s", e)
        except OSError as e:
            log.warning("Failed to kill worker for task %d: %s", task_id, e)
        self.post_message(WorkerKilled(task_id=task_id, next_task_id=next_task_id))

    def action_restart(self) -> None:
        if self._modal_active:
            return
        task_id = self.selected_task_id
        if task_id is None:
            self.notify("Select a worker first", title="No Selection", severity="error")
            return

        now = time.time()
        if self._pending_restart:
            pending_id, pending_time = self._pending_restart
            if pending_id == task_id and (now - pending_time) < 3.0:
                self._pending_restart = None
                self._execute_restart(task_id)
                return

        self._pending_restart = (task_id, now)
        self.notify(f"Press [bold]R[/] again within 3s to confirm", title=f"Restart task-{task_id}?", severity="warning")

    def _execute_restart(self, task_id: int) -> None:
        try:
            self.query_one("#status-bar", StatusBar).clear_flash()
        except NoMatches:
            pass
        session_name = f"task-{task_id}"
        worktree_path = task_worktree(task_id)

        if not worktree_path.is_dir():
            self.notify("Worktree not found. Worker may have been cleaned up.", severity="error")
            return

        try:
            kill_session(session_name)
            project_root_file = worktree_path / ".task" / "project_root"
            env_vars = {}
            if project_root_file.exists():
                env_vars["PROJECT_ROOT"] = project_root_file.read_text().strip()

            if not create_session(session_name, str(worktree_path), env_vars=env_vars or None):
                self.notify("Restart failed: tmux error", severity="error")
                return

            recovery_prompt = (
                f"Continue task #{task_id}. Review progress and proceed with TDD workflow."
            )
            session_id_file = worktree_path / ".task" / "session_id"
            resume_flag = (
                f"--resume {shlex.quote(session_id_file.read_text().strip())}"
                if session_id_file.exists()
                else ""
            )

            log_file = str(get_claude_home() / "worker_signals.log")
            claude_cmd = (
                f"trap 'echo \"$(date -u +%Y-%m-%dT%H:%M:%SZ) SIGTERM {session_name}\" >> {shlex.quote(log_file)}' SIGTERM; "
                f"set +m; claude {resume_flag} --permission-mode bypassPermissions "
                f"{shlex.quote(recovery_prompt)}; exec bash"
            )

            if not send_keys(session_name, claude_cmd):
                self.notify("Restart failed: send_keys error", severity="error")
                return

            subprocess.run(
                ["tmux", "bind", "-n", "F12", "detach-client"],
                capture_output=True,
                timeout=10,
            )

            self.notify(
                f"Worker task-{task_id} restarted. Press 'a' to attach.",
                title="Restart Complete",
            )
        except subprocess.TimeoutExpired:
            self.notify("Restart failed: operation timed out", severity="error")
        except OSError as e:
            self.notify(f"Restart failed: {e}", severity="error")

    def _get_task_ids_in_order(self) -> list[int]:
        row_cache = self.sidebar._row_cache
        if not row_cache:
            return []
        return list(row_cache.keys())

    def _navigate(self, delta: int) -> None:
        task_ids = self._get_task_ids_in_order()
        if not task_ids:
            return

        default_idx = 0 if delta > 0 else -1
        selected = self.selected_task_id
        if selected is None:
            self.selected_task_id = task_ids[default_idx]
        else:
            try:
                current_idx = task_ids.index(selected)
                new_idx = (current_idx + delta) % len(task_ids)
                self.selected_task_id = task_ids[new_idx]
            except ValueError:
                self.selected_task_id = task_ids[default_idx]

    def _get_inbox_screen(self):
        """Return the InboxScreen if it's currently active, else None."""
        if not self._modal_active:
            return None
        from .screens.inbox import InboxScreen

        screen = self.screen
        return screen if isinstance(screen, InboxScreen) else None

    def action_nav_next(self) -> None:
        """Navigate to next task (j key)."""
        inbox = self._get_inbox_screen()
        if inbox is not None:
            inbox._nav_next()
            return
        if self._modal_active:
            return
        self._navigate(1)

    def action_nav_prev(self) -> None:
        """Navigate to previous task (k key)."""
        inbox = self._get_inbox_screen()
        if inbox is not None:
            inbox._nav_prev()
            return
        if self._modal_active:
            return
        self._navigate(-1)

    def action_attach_focused(self) -> None:
        inbox = self._get_inbox_screen()
        if inbox is not None:
            if inbox._replying:
                inbox._submit_reply()
            else:
                inbox._open_reply()
            return
        if self._modal_active:
            return
        self.action_attach()

    def action_dismiss_blocked(self) -> None:
        """Dismiss a stale blocked worker (d key) — clears DB state."""
        inbox = self._get_inbox_screen()
        if inbox is not None:
            inbox._dismiss_blocked()
            return
