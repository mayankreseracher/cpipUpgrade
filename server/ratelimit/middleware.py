"""
Rate limiting middleware for FastAPI.
"""

from __future__ import annotations

import logging
from typing import Optional, Callable

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from server.ratelimit.bucket import RedisRateLimiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """HTTP middleware for rate limiting requests."""

    def __init__(
        self,
        app,
        limiter: RedisRateLimiter,
        get_client_id: Optional[Callable] = None,
        capacity: int = 100,
        refill_rate: float = 10.0,
    ):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            limiter: RedisRateLimiter instance
            get_client_id: Function to extract client ID from request
            capacity: Token bucket capacity
            refill_rate: Tokens refilled per second
        """
        super().__init__(app)
        self.limiter = limiter
        self.capacity = capacity
        self.refill_rate = refill_rate

        if get_client_id is None:
            self.get_client_id = self._default_get_client_id
        else:
            self.get_client_id = get_client_id

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for certain paths
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        client_id = self.get_client_id(request)

        allowed, remaining, reset_time = self.limiter.is_allowed(
            client_id,
            capacity=self.capacity,
            refill_rate=self.refill_rate,
        )

        if not allowed:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded. Retry after {reset_time}s",
                    "retry_after": reset_time,
                },
                headers={
                    "X-RateLimit-Limit": str(self.capacity),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.capacity)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _default_get_client_id(self, request: Request) -> str:
        """Extract client ID from request (IP or auth token)."""
        # Try to get from JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return f"token:{token[:20]}"  # Use token prefix

        # Fall back to client IP
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
