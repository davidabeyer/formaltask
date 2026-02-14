"""Inbox modal screen — view and respond to blocked workers."""

import logging
from typing import ClassVar

from textual import on, work
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Input, Static

log = logging.getLogger(__name__)


def _format_age(seconds: int | None) -> str:
    if seconds is None:
        return ""
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    return f"{seconds // 3600}h ago"


class InboxItem(Static):
    """One blocked worker card: header + title + question."""

    # CSS (not DEFAULT_CSS) to override theme.tcss Screen rules
    CSS = """
    InboxItem {
        height: auto;
        padding: 1 2;
        margin: 0 0 1 0;
        background: #181825;
        border-left: outer #313244;
    }
    InboxItem.--selected {
        border-left: outer #f9e2af;
    }
    """

    def __init__(self, worker: dict, **kwargs) -> None:
        self.worker = worker
        task_id = worker["task_id"]
        title = worker.get("task_title") or "Untitled"
        age = _format_age(worker.get("age_seconds"))
        question = worker.get("pending_question") or "No question provided"

        header = f"[bold #f9e2af]#{task_id}[/]  [dim #6c7086]{age}[/]"
        lines = [
            header,
            f"[#cdd6f4]{title}[/]",
            f"[italic #9399b2]{question}[/]",
        ]
        super().__init__("\n".join(lines), markup=True, **kwargs)


class InboxScreen(ModalScreen[None]):
    """Overlay showing blocked workers with response input.

    Uses CSS (not DEFAULT_CSS) so it overrides theme.tcss's
    Screen { background: #1e1e2e } which otherwise kills transparency.

    Uses on_key() for direct key handling to avoid App-level
    binding conflicts (App priority bindings consume events
    before Screen bindings fire).
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Close", priority=True),
    ]

    # CSS (not DEFAULT_CSS) — highest priority, overrides theme.tcss Screen rule
    CSS = """
    InboxScreen {
        background: $background 20%;
        align: center middle;
    }

    #inbox-container {
        width: 80%;
        max-width: 100;
        height: auto;
        background: #1e1e2e;
        border: round #f9e2af;
        border-title-align: left;
        border-title-color: #f9e2af;
        padding: 1 2;
    }

    #inbox-list {
        height: auto;
        max-height: 60;
        background: transparent;
    }

    #inbox-empty {
        color: #6c7086;
        text-align: center;
        padding: 2;
    }

    #inbox-response {
        display: none;
        margin-top: 1;
        background: #181825;
        border: tall #313244;
        color: #cdd6f4;
    }

    #inbox-response:focus {
        border: tall #f9e2af;
    }

    #inbox-response.visible {
        display: block;
    }

    #inbox-hints {
        color: #6c7086;
        text-align: center;
        margin-top: 1;
        height: 1;
    }
    """

    def __init__(self, blocked_workers: list[dict], db_path: str) -> None:
        super().__init__()
        self.blocked_workers = list(blocked_workers)
        self.db_path = db_path
        self.selected_index = 0
        self._replying = False
        self._sending = False

    def compose(self):
        with Vertical(id="inbox-container") as container:
            container.border_title = f" Inbox ({len(self.blocked_workers)} blocked) "
            if not self.blocked_workers:
                yield Static("No blocked workers", id="inbox-empty")
            else:
                with VerticalScroll(id="inbox-list"):
                    for i, worker in enumerate(self.blocked_workers):
                        item = InboxItem(worker, id=f"inbox-item-{i}")
                        if i == 0:
                            item.add_class("--selected")
                        yield item
                yield Input(
                    placeholder="Type response...",
                    id="inbox-response",
                )
            yield Static(
                "[dim #6c7086]j/k[/] Navigate  [dim #6c7086]Enter[/] Reply  [dim #6c7086]d[/] Dismiss  [dim #6c7086]Esc[/] Close",
                id="inbox-hints",
                markup=True,
            )

    def on_key(self, event: Key) -> None:
        """Handle keys directly — fallback for non-priority-bound keys.

        Note: j/k/enter/d are handled by App priority bindings that delegate
        to our methods. This handler catches escape (which has a Screen-level
        binding) and prevents unhandled keys from leaking through.
        """
        if self._replying:
            if event.key == "escape":
                event.stop()
                event.prevent_default()
                self._exit_reply_mode()
            return

        if event.key in ("j", "k", "enter", "d"):
            # Handled by App priority bindings — stop propagation as fallback
            event.stop()
            event.prevent_default()
        elif event.key == "escape":
            event.stop()
            event.prevent_default()
            self.dismiss(None)

    def _nav_next(self) -> None:
        if not self.blocked_workers:
            return
        self.selected_index = min(self.selected_index + 1, len(self.blocked_workers) - 1)
        self._update_selection()

    def _nav_prev(self) -> None:
        if not self.blocked_workers:
            return
        self.selected_index = max(self.selected_index - 1, 0)
        self._update_selection()

    def _update_selection(self) -> None:
        for i in range(len(self.blocked_workers)):
            try:
                item = self.query_one(f"#inbox-item-{i}", InboxItem)
                if i == self.selected_index:
                    item.add_class("--selected")
                else:
                    item.remove_class("--selected")
            except Exception:
                pass

    def _open_reply(self) -> None:
        if not self.blocked_workers:
            return
        self._replying = True
        worker = self.blocked_workers[self.selected_index]
        try:
            inp = self.query_one("#inbox-response", Input)
            inp.add_class("visible")
            inp.placeholder = f"Reply to #{worker['task_id']}..."
            inp.value = ""
            inp.focus()
            self.query_one("#inbox-hints", Static).update(
                "[dim #6c7086]Enter[/] Send  [dim #6c7086]Esc[/] Cancel"
            )
        except Exception:
            self._replying = False

    # Keep action_cancel for the Escape BINDING fallback
    def action_cancel(self) -> None:
        if self._replying:
            self._exit_reply_mode()
            return
        self.dismiss(None)

    def _exit_reply_mode(self) -> None:
        self._replying = False
        try:
            inp = self.query_one("#inbox-response", Input)
            inp.remove_class("visible")
            inp.value = ""
            self.query_one("#inbox-hints", Static).update(
                "[dim #6c7086]j/k[/] Navigate  [dim #6c7086]Enter[/] Reply  [dim #6c7086]d[/] Dismiss  [dim #6c7086]Esc[/] Close"
            )
        except Exception:
            pass

    def _submit_reply(self) -> None:
        """Submit typed response — fire-and-forget.

        Immediately removes the worker from the inbox and dismisses if empty.
        The actual resume runs in a background thread; notifications appear on
        the main dashboard when it completes or fails.
        """
        if self._sending:
            return
        try:
            inp = self.query_one("#inbox-response", Input)
            response = inp.value.strip()
            if not response:
                return
            self._sending = True
            worker = self.blocked_workers[self.selected_index]
            task_id = worker["task_id"]
            log.info("Sending response to task %d: %s", task_id, response[:80])

            # Fire background thread BEFORE dismissing (thread survives screen dismiss)
            self._send_response(task_id, response)

            # Immediately update inbox — don't wait for the 10s resume
            self.blocked_workers.pop(self.selected_index)
            if not self.blocked_workers:
                self.dismiss(None)
                return

            # More workers remain — refresh the list
            self.selected_index = min(self.selected_index, len(self.blocked_workers) - 1)
            self._replying = False
            self._sending = False
            self._refresh_inbox_list()
        except Exception:
            self._sending = False

    @on(Input.Submitted, "#inbox-response")
    def on_response_submitted(self, event: Input.Submitted) -> None:
        self._submit_reply()

    @work(thread=True)
    def _send_response(self, task_id: int, response: str) -> None:
        from formaltask.workers.resume import resume_worker_in_tmux

        try:
            resume_worker_in_tmux(task_id, response)
            self.app.call_from_thread(
                self.app.notify, f"Resumed task-{task_id}", severity="information"
            )
        except Exception as e:
            log.warning("Failed to resume task %d: %s", task_id, e)
            self.app.call_from_thread(
                self.app.notify, f"Resume task-{task_id} failed: {e}", severity="error"
            )

    def _refresh_inbox_list(self) -> None:
        """Rebuild inbox item list after removing a worker."""
        try:
            container = self.query_one("#inbox-container", Vertical)
            container.border_title = f" Inbox ({len(self.blocked_workers)} blocked) "

            scroll = self.query_one("#inbox-list", VerticalScroll)
            scroll.remove_children()
            for i, worker in enumerate(self.blocked_workers):
                item = InboxItem(worker, id=f"inbox-item-{i}")
                if i == self.selected_index:
                    item.add_class("--selected")
                scroll.mount(item)

            inp = self.query_one("#inbox-response", Input)
            inp.remove_class("visible")
            inp.value = ""
            self.query_one("#inbox-hints", Static).update(
                "[dim #6c7086]j/k[/] Navigate  [dim #6c7086]Enter[/] Reply  [dim #6c7086]d[/] Dismiss  [dim #6c7086]Esc[/] Close"
            )
        except Exception:
            pass

    def _dismiss_blocked(self) -> None:
        """Dismiss a stale blocked worker — clears blocked_question in DB."""
        if not self.blocked_workers or self._replying:
            return
        worker = self.blocked_workers[self.selected_index]
        task_id = worker["task_id"]
        log.info("Dismissing blocked worker task %d", task_id)

        # Clear blocked state in DB (background thread)
        self._clear_blocked_in_db(task_id)

        # Immediately remove from inbox
        self.blocked_workers.pop(self.selected_index)
        if not self.blocked_workers:
            self.dismiss(None)
            return
        self.selected_index = min(self.selected_index, len(self.blocked_workers) - 1)
        self._refresh_inbox_list()

    @work(thread=True)
    def _clear_blocked_in_db(self, task_id: int) -> None:
        from formaltask.workers.resume import _clear_blocked_state

        try:
            _clear_blocked_state(task_id)
            self.app.call_from_thread(
                self.app.notify, f"Dismissed task-{task_id}", severity="information"
            )
        except Exception as e:
            log.warning("Failed to clear blocked state for task %d: %s", task_id, e)
            self.app.call_from_thread(
                self.app.notify, f"Dismiss failed: {e}", severity="error"
            )
