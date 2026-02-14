"""Task list widget for dashboard display."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from textual.app import ComposeResult
from textual.widgets import Static

from ..formatters import BLOCKED_STATES, IDLE_STATES, get_sidebar_status
from .task_row import TaskRow, TaskRowData

# Health states where missing tmux is expected (not a zombie)
_IDLE_HEALTH_STATES = IDLE_STATES | BLOCKED_STATES | {"unknown", "queued"}

# Title max length for sidebar display
SIDEBAR_TITLE_MAX = 74

# Task #2848: Sort order for sidebar - queued always last
STATUS_ORDER = {"error": 0, "running": 1, "spawn": 1.5, "idle": 2, "queued": 3}


class TaskList(Static):
    """Sidebar widget for displaying task list sorted by urgency.

    Border title shows "Tasks" embedded in the border line.
    Tasks are displayed as a flat list: active workers + queued (spawnable) tasks.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize with border title."""
        super().__init__(*args, **kwargs)
        self.border_title = "Tasks"
        self._row_cache: dict[int, TaskRow] | None = None
        self._selected_task_id: int | None = None
        self._spawnable_ids: list[int] = []
        self._spawnable_tasks: list[dict] = []
        self._prev_phases: dict[int, str] = {}  # task_id -> previous phase
        self._change_counter: int = 0
        self._separator: Static | None = None
        self._separator_bottom: Static | None = None
        self._killed_task_ids: set[int] = set()

    @property
    def selected_task_id(self) -> int | None:
        """Currently selected task ID."""
        return self._selected_task_id

    @property
    def spawnable_ids(self) -> list[int]:
        """List of task IDs that are ready to spawn."""
        return self._spawnable_ids

    def compose(self) -> ComposeResult:
        """Compose sidebar - tasks added dynamically via mount()."""
        yield from []

    def update_selection(self, task_id: int | None) -> None:
        """Update which TaskRow is selected. O(1) using row cache."""
        old_id = self._selected_task_id
        self._selected_task_id = task_id

        # Build cache on first call or if stale
        if self._row_cache is None:
            self._rebuild_row_cache()

        # O(1) deselect old row
        if old_id is not None and self._row_cache and old_id in self._row_cache:
            self._row_cache[old_id].remove_class("--selected")

        # O(1) select new row + clear NEW tag
        if task_id is not None and self._row_cache and task_id in self._row_cache:
            self._row_cache[task_id].add_class("--selected")
            row = self._row_cache[task_id]
            if row.data.is_new:
                row.data.is_new = False
                row.refresh()

    def kill_task(self, task_id: int) -> None:
        """Eagerly remove a killed task's row from the list.

        Adds task_id to _killed_task_ids so refresh_from_states skips it
        until the poll confirms the task is truly gone.
        """
        self._killed_task_ids.add(task_id)
        if self._row_cache and task_id in self._row_cache:
            self._row_cache[task_id].remove()
            del self._row_cache[task_id]
            self._prev_phases.pop(task_id, None)

    def _rebuild_row_cache(self) -> None:
        """Rebuild task_id → TaskRow cache. Called after DOM changes."""
        self._row_cache = {row.data.task_id: row for row in self.query(TaskRow)}

    def refresh_from_states(
        self,
        states: dict[int, dict[str, Any]],
        selected_id: int | None,
        spawnable_ids: list[int] | None = None,
        spawnable_tasks: list[dict] | None = None,
    ) -> None:
        """Transform raw worker states into TaskRowData and update flat list.

        Task #2822: Simplified to flat urgency-sorted list (no epic grouping).
        Task #2784: Uses differential updates to avoid DOM flashing.

        Args:
            states: Dict mapping task_id to raw worker state dict.
            selected_id: Currently selected task ID for selection preservation.
            spawnable_ids: List of task IDs ready to spawn (for QUEUE section).
            spawnable_tasks: List of dicts with 'id' and 'title' for queue display.
        """
        # Store spawnable_ids for action_spawn() to access
        self._spawnable_ids = spawnable_ids if spawnable_ids is not None else []
        self._spawnable_tasks = spawnable_tasks if spawnable_tasks is not None else []

        # Clean up _killed_task_ids: clear entries confirmed absent from states
        if self._killed_task_ids:
            confirmed_gone = self._killed_task_ids - set(states.keys())
            self._killed_task_ids -= confirmed_gone

        # Filter out killed task_ids from states to suppress re-creation
        states = {tid: s for tid, s in states.items() if tid not in self._killed_task_ids}

        # Build cache if needed (Task #2784: keep cache valid across refreshes)
        if self._row_cache is None:
            self._row_cache = {}
            for widget in self.query(TaskRow):
                self._row_cache[widget.data.task_id] = widget

        # Combine active workers + spawnable tasks
        # Spawnable tasks shown as "queued" status (sort last)
        spawnable_ids_set = set(self._spawnable_ids)
        new_task_ids = set(states.keys()) | spawnable_ids_set
        old_task_ids = set(self._row_cache.keys())

        # Remove orphaned rows (tasks no longer in states or spawnable)
        for task_id in old_task_ids - new_task_ids:
            if task_id in self._row_cache:
                self._row_cache[task_id].remove()
                del self._row_cache[task_id]
                self._prev_phases.pop(task_id, None)

        # Transform active worker states to TaskRowData
        task_rows = [self._state_to_row_data(tid, s) for tid, s in states.items()]

        # Track NEW tag: set is_new when phase changes between polls
        for row_data in task_rows:
            prev_phase = self._prev_phases.get(row_data.task_id)
            if prev_phase is not None and prev_phase != row_data.phase:
                row_data.is_new = True
                self._change_counter += 1
            self._prev_phases[row_data.task_id] = row_data.phase

        # Add spawnable tasks as "queued" TaskRowData (exclude any already in states)
        queued_rows: list[TaskRowData] = []
        for task in self._spawnable_tasks:
            task_id = task.get("id", 0)
            if task_id not in states:
                queued_rows.append(
                    TaskRowData(
                        task_id=task_id,
                        title=task.get("title", "")[:SIDEBAR_TITLE_MAX],
                        status="queued",
                        phase="queued",
                        elapsed_seconds=0,
                    )
                )

        # Sort active rows by urgency, then by task_id
        task_rows.sort(key=lambda r: (STATUS_ORDER.get(r.status, 2), r.task_id))
        queued_rows.sort(key=lambda r: r.task_id)

        # Safety promote: EXIT/HELP phases stay in active list (already above queued)
        # This is guaranteed by STATUS_ORDER: error(0) > running(1) > idle(2) > queued(3)

        # Update existing rows or create new ones (differential updates)
        for row_data in task_rows:
            task_id = row_data.task_id
            if task_id in self._row_cache:
                self._row_cache[task_id].update_from_state(row_data)
            else:
                row = TaskRow(row_data)
                self._row_cache[task_id] = row
                self.mount(row)

        # Mount queue separator if there are queued tasks
        if queued_rows:
            sep_text = f"╶── {len(queued_rows)} queued ──╴"
            if self._separator is None:
                self._separator = Static(sep_text, classes="queue-separator")
                self.mount(self._separator)
            else:
                self._separator.update(sep_text)

            for row_data in queued_rows:
                task_id = row_data.task_id
                if task_id in self._row_cache:
                    self._row_cache[task_id].update_from_state(row_data)
                else:
                    row = TaskRow(row_data)
                    self._row_cache[task_id] = row
                    self.mount(row)

            # Bottom separator between queued and active sections
            if task_rows and self._separator_bottom is None:
                self._separator_bottom = Static("", classes="queue-separator-bottom")
                self.mount(self._separator_bottom)
        else:
            if self._separator is not None:
                self._separator.remove()
                self._separator = None
            if self._separator_bottom is not None:
                self._separator_bottom.remove()
                self._separator_bottom = None

        self.update_selection(selected_id)

    def _state_to_row_data(self, task_id: int, state: dict[str, Any]) -> TaskRowData:
        """Transform raw worker state to TaskRowData.

        Encapsulates the transformation logic that was in app.py._update_sidebar.

        Args:
            task_id: The task ID.
            state: Raw worker state dict from fetch_worker_states.

        Returns:
            TaskRowData with all fields populated from the raw state.
        """
        # Derive status via get_sidebar_status (Task #2412)
        health = state.get("health_state", "unknown")
        tmux_exists = state.get("tmux_session_exists", False)
        status = get_sidebar_status(health, tmux_exists)

        # Calculate elapsed seconds from session start time
        # Task #2247: Prefer session_started_at (tmux creation time) for accurate elapsed
        # Falls back to started_at (task start from DB) if session not available
        elapsed_seconds = 0
        started_at = state.get("session_started_at") or state.get("started_at", "")
        if started_at:
            try:
                start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                elapsed_seconds = int((datetime.now(UTC) - start_time).total_seconds())
            except (ValueError, TypeError):
                pass

        # Row marker: '!' for error/zombie, '?' for blocked question, ' ' default
        blocked_question = state.get("pending_question")
        is_zombie = not tmux_exists and health not in _IDLE_HEALTH_STATES
        if status == "error" or is_zombie:
            row_marker = "!"
        elif blocked_question is not None:
            row_marker = "?"
        else:
            row_marker = " "

        return TaskRowData(
            task_id=task_id,
            title=state.get("title", "")[:SIDEBAR_TITLE_MAX],
            status=status,
            phase=state.get("health_state", "unknown"),
            elapsed_seconds=elapsed_seconds,
            blocked_question=blocked_question,
            is_stale=state.get("is_stale", False),
            epic_name=state.get("epic_name"),
            row_marker=row_marker,
            spawn_dots=state.get("spawn_dots", ""),
        )
