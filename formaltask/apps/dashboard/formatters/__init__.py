"""Dashboard formatters — display-ready conversions for widgets."""

from .worker_activity import format_selected_worker_terminal

BLOCKED_STATES: frozenset[str] = frozenset({"blocked", "error", "needs_human"})
IDLE_STATES: frozenset[str] = frozenset({"exited", "completed", "awaiting_merge", "done"})


def get_sidebar_status(health_state: str, tmux_exists: bool) -> str:
    """Map health state to sidebar group: error / running / idle.

    Priority: BLOCKED_STATES → IDLE_STATES → tmux_exists → "idle"
    """
    if health_state in BLOCKED_STATES:
        return "error"
    if health_state in IDLE_STATES:
        return "idle"
    if tmux_exists:
        return "running"
    return "idle"


__all__ = [
    "BLOCKED_STATES",
    "IDLE_STATES",
    "format_selected_worker_terminal",
    "get_sidebar_status",
]
