"""Token bucket rate limiter per API key."""

import time


class RateLimiter:
    """Token bucket rate limiter with per-key tracking.

    Args:
        max_tokens: Maximum tokens per bucket (burst size).
        refill_rate: Tokens added per second.
    """

    def __init__(self, max_tokens: int, refill_rate: float):
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_time)

    def allow(self, key: str) -> bool:
        """Check if a request is allowed for the given key.

        Returns True and consumes a token, or False if no tokens remain.
        """
        now = time.monotonic()

        if key in self._buckets:
            tokens, last_time = self._buckets[key]
            elapsed = now - last_time
            tokens = min(self.max_tokens, tokens + elapsed * self.refill_rate)
        else:
            tokens = float(self.max_tokens)

        if tokens >= 1.0:
            self._buckets[key] = (tokens - 1.0, now)
            return True

        self._buckets[key] = (tokens, now)
        return False
