"""dashboard - TUI for monitoring parallel workers."""

import argparse

from formaltask.apps.dashboard import WorkerDashboard
from formaltask.db.path import get_db_path


# STUB: No arguments needed - dashboard has no CLI options
def setup_parser(subparser: argparse.ArgumentParser) -> None:
    """Configure argument parser for dashboard command."""


def execute(args: argparse.Namespace) -> int:
    """Launch the WorkerDashboard TUI."""
    db_path = get_db_path()
    app = WorkerDashboard(db_path=db_path)
    app.run()
    return 0
