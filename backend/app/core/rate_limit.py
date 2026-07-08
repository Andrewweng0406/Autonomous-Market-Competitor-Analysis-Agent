"""A minimal in-memory fixed-window rate limiter.

Each `/api/analyze` call triggers several Claude API calls (plan, multiple
searches, synthesis) plus external search-provider calls, so an unthrottled
endpoint is an easy way to run up a large bill or get rate-limited by
Anthropic. This is intentionally simple — a fixed window per client IP is
enough to stop accidental abuse (e.g. a retry loop, a scripted load test)
without adding an external dependency (Redis) to this skeleton.

For a multi-process/multi-node deployment, replace this with a shared store
(Redis `INCR` + `EXPIRE` is the standard pattern) so limits are enforced
across all instances rather than per-process.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict


class RateLimiter:
    """Fixed-window request limiter keyed by an arbitrary string (e.g. client IP)."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self._window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        """Returns True and records the hit if `key` is under its limit,
        otherwise returns False without recording anything.
        """
        now = time.monotonic()
        window_start = now - self._window_seconds
        hits = self._hits[key]

        while hits and hits[0] < window_start:
            hits.popleft()

        if len(hits) >= self.max_requests:
            return False

        hits.append(now)
        return True

    def retry_after_seconds(self, key: str) -> int:
        """Best-effort hint for how long the client should wait before retrying."""
        hits = self._hits.get(key)
        if not hits:
            return self._window_seconds
        elapsed = time.monotonic() - hits[0]
        return max(1, int(self._window_seconds - elapsed))
