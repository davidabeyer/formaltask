"""Dashboard visual constants."""

from formaltask.utils.constants import WorkerPhase

# State markers for sidebar status - single character indicators
STATE_MARKERS: dict[str, str] = {
    "error": "!",
    "idle": "?",
    "running": " ",
    "queued": " ",
}

# State styles for worker status display - Catppuccin Mocha palette
# Note: WorkerPhase enums are used for derived phases. Due to StrEnum equality,
# lookups by string (e.g., "blocked") still work with WorkerPhase keys.
STATE_STYLES: dict[str | WorkerPhase, str] = {
    "working": "bold #a6e3a1",  # Catppuccin Green
    "ready": "bold #89dceb",  # Catppuccin Sky/Cyan
    WorkerPhase.BLOCKED: "bold #f38ba8",  # Catppuccin Red (WorkerPhase + health state)
    "completed": "dim #a6e3a1",  # Dim green
    "error": "bold #f38ba8 reverse",  # Red with highlight
    "unknown": "dim #6c7086",  # Catppuccin Overlay0
    "waiting_input": "bold #f9e2af",  # Catppuccin Yellow
    "waiting": "#f9e2af",  # Yellow
    "recovering": "bold #cba6f7",  # Catppuccin Mauve
    "exited": "dim #9399b2",  # Catppuccin Overlay2 - greyed out, dead
    # Derived phases from derive_worker_phase() - use WorkerPhase enum keys
    WorkerPhase.IMPLEMENTING: "bold #a6e3a1",  # Green - active coding
    WorkerPhase.NEEDS_FIX: "bold #fab387",  # Orange - P2/P3 findings, worker can fix
    WorkerPhase.NEEDS_HUMAN: "bold #f38ba8",  # Red - P0/P1 findings, needs human review
    WorkerPhase.NEEDS_PR: "bold #89b4fa",  # Blue - clean reviews, needs PR
    WorkerPhase.AWAITING_MERGE: "#89dceb",  # Cyan - PR exists, waiting for merge
    WorkerPhase.DONE: "dim #a6e3a1",  # Dim green - completed (same as "completed")
    "queued": "dim #6c7086",  # Muted - waiting to spawn
    "spawn": "bold #cba6f7",  # Mauve - spawning worker
    "slow": "bold #fab387",  # Orange - slow worker
    "c1": "bold #89b4fa",  # Blue - cycle 1
    "exec": "bold #a6e3a1",  # Green - executing
}

# Timing constants
POLL_INTERVAL: float = 1.0  # seconds - default polling interval
POLL_INTERVAL_FAST: float = 0.2  # seconds - during active content changes
POLL_IDLE_THRESHOLD: int = 5  # consecutive no-change polls before slowing down
FETCH_TIMEOUT: float = 5.0  # seconds - timeout for fetch operations
