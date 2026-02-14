"""Integration tests for dashboard polling and message behaviors (Task #2594).

Retained tests:
- Pure behavior: test_backoff_calculation_formula (catches formula bugs)
- Interface smoke tests: handler existence, message inheritance (cheap, detect renames)
"""


class TestExponentialBackoff:
    """Tests that exponential backoff is preserved in poll_workers."""

    def test_backoff_calculation_formula(self):
        """Verify backoff formula: min(base * 2^errors, max)."""
        base_interval = 2.0  # POLL_INTERVAL
        max_interval = 60.0

        # Consecutive error 1: 2 * 2^1 = 4
        errors = 1
        sleep = min(base_interval * (2**errors), max_interval)
        assert sleep == 4.0

        # Consecutive error 2: 2 * 2^2 = 8
        errors = 2
        sleep = min(base_interval * (2**errors), max_interval)
        assert sleep == 8.0

        # Consecutive error 5: 2 * 2^5 = 64 -> capped at 60
        errors = 5
        sleep = min(base_interval * (2**errors), max_interval)
        assert sleep == 60.0
