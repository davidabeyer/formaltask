"""Formatter for selected worker terminal output."""

from rich.text import Text


def format_selected_worker_terminal(
    task_id: int | None,
    blocked_count: int = 0,
    captured_content: str | None = None,
) -> Text:
    """Render selected worker's tmux terminal output.

    Args:
        task_id: Selected task ID, or None if no worker selected.
        blocked_count: Number of blocked workers for inbox hint.
        captured_content: Pre-captured terminal content (from poll_workers thread).

    Returns:
        Rich Text object with full tmux output for the selected worker.
    """
    if task_id is None:
        return Text("Select a worker to view terminal", style="dim")

    output = captured_content or ""

    if output.strip():
        result = Text.from_ansi(output)
    else:
        result = Text("No output captured", style="dim")

    if blocked_count > 0:
        result.append(f"\n\n📥 {blocked_count} blocked - press i for inbox", style="dim")

    return result
