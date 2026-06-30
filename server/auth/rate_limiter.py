"""
Rate limiter using in-memory storage (Redis-ready).

Implements sliding window rate limiting per client.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request, status


@dataclass
class RateLimit:
    requests: int
    window_seconds: int


class RateLimiter:
    """In-memory sliding window rate limiter."""

    def __init__(self):
        self._windows: dict[str, list[float]] = defaultdict(list)

    def _client_key(self, request: Request | None) -> str:
        if request is None:
            return "rate:unknown"
        forwarded = request.headers.get("x-forwarded-for") if hasattr(request, "headers") else None
        ip = forwarded.split(",")[0].strip() if forwarded else request.client.host if getattr(request, "client", None) else "unknown"
        return f"rate:{ip}"

    def check(self, request: Request | None, limit: RateLimit) -> bool:
        if request is None:
            return True
        key = self._client_key(request)
        now = time.time()
        window_start = now - limit.window_seconds

        # Clean old entries
        self._windows[key] = [t for t in self._windows[key] if t > window_start]

        # Periodically prune empty keys to prevent memory leak
        if len(self._windows) > 1000:
            for k in list(self._windows.keys()):
                if not self._windows[k] or all(t <= window_start for t in self._windows[k]):
                    self._windows.pop(k, None)

        if len(self._windows[key]) >= limit.requests:
            return False

        self._windows[key].append(now)
        return True

    def remaining(self, request: Request | None, limit: RateLimit) -> int:
        if request is None:
            return limit.requests
        key = self._client_key(request)
        now = time.time()
        window_start = now - limit.window_seconds
        current = sum(1 for t in self._windows.get(key, []) if t > window_start)
        return max(0, limit.requests - current)


# Global instance
rate_limiter = RateLimiter()

# Default limits
DEFAULT_LIMIT = RateLimit(requests=100, window_seconds=60)
BUILD_LIMIT = RateLimit(requests=10, window_seconds=60)
EXEC_LIMIT = RateLimit(requests=50, window_seconds=60)


def check_rate_limit(request: Request | None, limit: RateLimit = DEFAULT_LIMIT) -> None:
    """Check rate limit and raise 429 if exceeded."""
    if request is None:
        return
    if not rate_limiter.check(request, limit):
        retry_after = limit.window_seconds
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {retry_after}s",
            headers={"Retry-After": str(retry_after)},
        )
