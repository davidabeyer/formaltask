"""Always-on terminal pane showing selected worker's tmux output."""

from rich.text import Text
from textual.widgets import Static

from formaltask.apps.dashboard.formatters import format_selected_worker_terminal


class TerminalPane(Static):
    """Persistent widget showing the selected worker's terminal output."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "Terminal"
        self._task_id: int | None = None
        self._captured_content: str | None = None
        self._blocked_count: int = 0

    def update_content(
        self,
        task_id: int | None,
        captured_content: str | None = None,
        blocked_count: int = 0,
    ) -> None:
        """Update stored state and refresh display."""
        self._task_id = task_id
        self._blocked_count = blocked_count

        # Trim to widget height, keeping the BOTTOM (most recent) lines.
        # capture_pane grabs ~50 lines but widget may only display ~20.
        # Static renders top-down, so without trimming we show stale content.
        if captured_content:
            visible = self.content_size.height if self.content_size.height > 0 else 20
            lines = captured_content.split("\n")
            if len(lines) > visible:
                captured_content = "\n".join(lines[-visible:])

        self._captured_content = captured_content
        self.update(self.render_content())

    def render_content(self) -> Text:
        """Produce Rich Text from current state."""
        return format_selected_worker_terminal(
            self._task_id,
            blocked_count=self._blocked_count,
            captured_content=self._captured_content,
        )

    def on_mount(self) -> None:
        self.update(self.render_content())
