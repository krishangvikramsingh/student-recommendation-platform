import threading
import time
from collections import deque

from srp.errors import RateLimited


class RateLimiter:
    """Sliding-window limiter keyed by an arbitrary string (client address, email, ...)."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.hits = {}
        self._lock = threading.Lock()
        self._swept = clock()

    def check(self, key, limit, window):
        now = self.clock()
        with self._lock:
            if now - self._swept > 300:
                self._sweep(now)
            queue = self.hits.setdefault(key, deque())
            while queue and now - queue[0] > window:
                queue.popleft()
            if len(queue) >= limit:
                raise RateLimited(int(window - (now - queue[0])) + 1)
            queue.append(now)

    def _sweep(self, now):
        self._swept = now
        for key in [k for k, q in self.hits.items() if not q or now - q[-1] > 3600]:
            del self.hits[key]
