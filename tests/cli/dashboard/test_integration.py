"""Integration smoke test for WorkerDashboard.

Task #2349: End-to-end smoke test that exercises dashboard navigation and basic operations.
This is a smoke test - verifies no crashes with minimal assertions per PRP constraints.
"""

import pytest

from formaltask.apps.dashboard import WorkerDashboard


@pytest.mark.asyncio
async def test_dashboard_integration_smoke() -> None:
    """Launch dashboard, navigate, toggle, quit - no regressions.

    Exercises:
    - Navigation: j/k keys (down/up) - graceful no-op when empty
    - Exit: q key (quit)

    Minimal assertions verify core smoke test criteria without exhaustive coverage.
    """
    app = WorkerDashboard()
    async with app.run_test() as pilot:
        assert app.is_running, "Dashboard should be running after launch"

        # Navigate down/up with vim keys (graceful no-op when no workers)
        await pilot.press("j")
        await pilot.press("k")

        # Quit main app
        await pilot.press("q")
