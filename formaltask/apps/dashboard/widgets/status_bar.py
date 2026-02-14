"""StatusBar widget for dashboard status display."""

import time

from rich.text import Text
from textual.widgets import Static

SEVERITY_STYLES = {
    "information": ("\u25cf", "#a6e3a1"),  # ● green
    "warning": ("\u25cf", "#fab387"),  # ● peach
    "error": ("\u25cf", "#f38ba8"),  # ● red
}


class StatusBar(Static):
    """Status bar showing epic count, task counts, and clock."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._epic_count = 0
        self._done = 0
        self._running_count = 0
        self._exit_count = 0
        self._help_count = 0
        self._queued = 0
        self._change_count = 0
        self._total = 0
        self._last_update_time: float = 0.0
        self._flash_until: float | None = None
        self._flash_title: str = ""
        self._flash_message: str = ""
        self._flash_severity: str = "information"
        self._activity: str = ""

    def update(  # type: ignore[override]
        self,
        *,
        epic_count: int,
        done: int,
        running: int,
        exit_count: int,
        help_count: int,
        queued: int,
        change_count: int,
    ) -> None:
        """Store pre-computed counts for rendering."""
        self._epic_count = epic_count
        self._done = done
        self._running_count = running
        self._exit_count = exit_count
        self._help_count = help_count
        self._queued = queued
        self._change_count = change_count
        self._total = done + running + exit_count + help_count + queued
        self._last_update_time = time.monotonic()
        self.refresh()

    def flash(
        self,
        message: str,
        *,
        title: str = "",
        severity: str = "information",
        timeout: float = 3.0,
    ) -> None:
        """Flash a notification in the status bar, reverting after timeout."""
        self._flash_message = message
        self._flash_title = title
        self._flash_severity = severity
        self._flash_until = time.monotonic() + timeout
        self.refresh()

    def clear_flash(self) -> None:
        """Immediately clear any active flash."""
        self._flash_until = None
        self.refresh()

    def set_activity(self, text: str) -> None:
        """Set persistent activity text shown after the clock (e.g. auto-spawn status)."""
        self._activity = text
        self.refresh()

    def _render_flash(self) -> Text:
        """Render the flash notification line."""
        icon, color = SEVERITY_STYLES.get(self._flash_severity, ("\u25cf", "#89b4fa"))
        result = Text()
        result.append(f" {icon} ", style=color)
        if self._flash_title:
            result.append(self._flash_title, style=f"bold {color}")
            result.append("  ", style="")
        # Strip Rich markup tags for plain Text rendering
        plain = self._flash_message
        for tag in ("[bold]", "[/bold]", "[/]", "[bold green]"):
            plain = plain.replace(tag, "")
        result.append(plain, style="#cdd6f4")
        return result

    def render(self) -> Text:
        """Build Rich Text status line from stored counts."""
        # Flash message takes over the bar temporarily
        if self._flash_until is not None:
            if time.monotonic() < self._flash_until:
                return self._render_flash()
            self._flash_until = None

        sep = " \u00b7 "  # middle dot separator
        result = Text()

        # Epic count: hide when <= 1
        if self._epic_count > 1:
            result.append(f"{self._epic_count} epics", style="bold #cdd6f4")
            result.append(sep)

        result.append(f"{self._done}/{self._total} done", style="#a6e3a1")
        result.append(sep)
        result.append(f"{self._running_count} run", style="bold #a6e3a1")
        if self._exit_count:
            result.append(sep)
            result.append(f"{self._exit_count} EXIT", style="bold #f38ba8")
        if self._help_count:
            result.append(sep)
            result.append(f"{self._help_count} HELP", style="bold #f9e2af")
        result.append(sep)
        result.append(f"{self._queued} queued", style="dim #6c7086")
        if self._change_count:
            result.append(sep)
            result.append(f"\u2191{self._change_count}", style="#89b4fa")
        # Auto-spawn activity indicator
        if self._activity:
            result.append(sep)
            result.append(self._activity, style="#89dceb")
        return result

    def on_mount(self) -> None:
        """Start clock tick on mount."""
        self._clock_timer = self.set_interval(1.0, self.refresh)

    def on_unmount(self) -> None:
        """Stop clock tick on unmount."""
        self._clock_timer.stop()
