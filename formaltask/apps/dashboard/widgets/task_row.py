"""TaskRow widget for displaying a single task in the sidebar."""

from dataclasses import dataclass

from rich.text import Text
from textual.widgets import Static

from ..constants import STATE_STYLES

# Phase badge display: (text, color) - Catppuccin Mocha adjusted for visibility
PHASE_BADGES: dict[str, tuple[str, str]] = {
    "implementing": ("IMPL", "#a6e3a1"),  # green - active work
    "needs_fix": ("FIX", "#fab387"),  # orange - needs attention
    "needs_human": ("HELP", "#f38ba8"),  # red - blocked
    "needs_pr": ("PR", "#89b4fa"),  # blue - ready for PR
    "awaiting_merge": ("WAIT", "#94e2d5"),  # teal - waiting on merge
    "done": ("DONE", "#585b70"),  # dim - completed
    "blocked": ("STOP", "#f38ba8"),  # red - blocked
    "needs_reflection": ("REFL", "#f9e2af"),  # yellow - needs review
    "exited": ("EXIT", "#f38ba8"),  # red - terminated (bold red escalation)
    "queued": ("QUEUE", "#6c7086"),  # muted - waiting to spawn
    "unknown": ("?", "#585b70"),  # dim - unknown state
    "spawn": ("SPAWN", "#cba6f7"),  # mauve - spawning worker
    "slow": ("SLOW", "#fab387"),  # orange - slow worker
    "c1": ("C1", "#89b4fa"),  # blue - cycle 1
    "exec": ("EXEC", "#a6e3a1"),  # green - executing
}


@dataclass
class TaskRowData:
    """Data for a single task row in the sidebar."""

    task_id: int
    title: str
    status: str  # Sidebar grouping: error/running/idle/queued
    phase: str  # Worker phase: implementing/needs_fix/queued/etc
    elapsed_seconds: int
    blocked_question: str | None = None  # Question when worker is blocked
    epic_name: str | None = None  # Epic name for grouping
    is_stale: bool = False  # Task #2810: Worker is stale (dim visual indicator)
    row_marker: str = " "  # Selection/status marker character
    is_new: bool = False  # Recently spawned task indicator
    spawn_dots: str = ""  # Spawn progress dots (e.g. "●●")


class TaskRow(Static):
    """Single task row widget for sidebar display."""

    def __init__(self, data: TaskRowData) -> None:
        """Initialize TaskRow with task data."""
        super().__init__()
        self.data = data

    def render(self) -> Text:
        """Render the task row display.

        Layout: [marker][epic:20] [#id] [title...] [BADGE] [time] [NEW]
        """
        result = Text()
        width = self.size.width if self.size.width > 0 else 40

        # Status-based style
        if self.data.is_stale:
            style = "dim #9399b2"
        elif self.data.phase == "done":
            # Three-tier dimming for DONE tasks based on elapsed time
            if self.data.elapsed_seconds < 300:
                style = "dim #a6e3a1"  # green - recently done
            elif self.data.elapsed_seconds < 1800:
                style = "dim #585b70"  # medium dim
            else:
                style = "dim #45475a"  # very dim - old
        else:
            style_key = "working" if self.data.status == "running" else self.data.status
            style = STATE_STYLES.get(style_key, "dim #9399b2")

        # [marker] - 1 char: ▸ for selected rows, original marker otherwise
        marker = "\u25b8" if self.has_class("--selected") else self.data.row_marker
        result.append(marker, style=style)

        # [epic:20] - italic dim mauve, None→blank
        epic = (self.data.epic_name or "")[:20].ljust(20)
        result.append(epic, style="italic dim #cba6f7")

        # [#id] + space
        task_id_str = f" #{self.data.task_id} "
        result.append(task_id_str, style=style)

        # Right side: [BADGE] [time] [NEW?]
        badge_text, badge_color = PHASE_BADGES.get(self.data.phase, ("?", "#6c7086"))
        # B2: spawn_dots override badge when phase is 'spawn'
        if self.data.phase == "spawn" and self.data.spawn_dots:
            badge_text = self.data.spawn_dots
        badge_padded = badge_text.ljust(5)
        minutes = self.data.elapsed_seconds // 60
        elapsed_str = f"{minutes}m".rjust(5)
        new_tag = " NEW" if self.data.is_new else ""

        # Fixed right section length
        right_len = 5 + 1 + 5 + len(new_tag)  # badge + space + time + new

        # [title...] fills remaining space
        left_used = 1 + 20 + len(task_id_str)
        title_width = max(width - left_used - right_len, 4)
        title = self.data.title[:title_width].ljust(title_width)
        result.append(title, style=style)

        # Badge
        result.append(badge_padded, style=f"bold {badge_color}")
        result.append(" ")
        # Time
        result.append(elapsed_str, style="dim #6c7086")
        # NEW tag
        if self.data.is_new:
            result.append(" NEW", style="bold #f9e2af")

        return result

    def update_from_state(self, state: TaskRowData) -> None:
        """Update row data without remounting.

        Task #2784: Used for differential updates to avoid DOM flashing.
        Only refreshes if data actually changed.

        Args:
            state: New TaskRowData to update the row with.
        """
        # Skip refresh if data unchanged (avoid DOM flash)
        if self.data == state:
            return
        self.data = state
        self.refresh()
