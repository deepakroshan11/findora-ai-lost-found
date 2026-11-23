"""In-memory sliding-window rate limiter (per key, e.g. client IP).

Good enough for one Render instance protecting a free LLM quota. If the backend
is ever scaled to several instances, move this to Redis.
"""
import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    def __init__(self, max_calls: int, window_seconds: float, clock=time.monotonic):
        self.max_calls = max_calls
        self.window = window_seconds
        self._clock = clock
        self._hits = defaultdict(deque)

    def allow(self, key: str) -> bool:
        """Record a call for `key`; return False if it would exceed the limit."""
        now = self._clock()
        hits = self._hits[key]
        while hits and now - hits[0] >= self.window:
            hits.popleft()
        if len(hits) >= self.max_calls:
            return False
        hits.append(now)
        self._prune(now)
        return True

    def _prune(self, now: float) -> None:
        """Drop idle keys so memory cannot grow without bound."""
        if len(self._hits) < 5000:
            return
        for key in [k for k, h in self._hits.items() if not h or now - h[-1] >= self.window]:
            del self._hits[key]
