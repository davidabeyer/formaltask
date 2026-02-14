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
        self._captured_content = captured_content
        self._blocked_count = blocked_count
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
