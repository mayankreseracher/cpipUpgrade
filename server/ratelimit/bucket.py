"""
Token bucket rate limiter implementation.

Provides per-client rate limiting using token bucket algorithm
with Redis backing for distributed deployments.
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class TokenBucket:
    """In-memory token bucket for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()

    def refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were available, False otherwise
        """
        self.refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def available_tokens(self) -> float:
        """Get current available tokens."""
        self.refill()
        return self.tokens


class RedisRateLimiter:
    """Distributed rate limiter using Redis."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "ratelimit:",
    ):
        """
        Initialize Redis rate limiter.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for rate limit keys
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.redis = None

        try:
            self.redis = redis.from_url(redis_url, decode_responses=True)
            self.redis.ping()
            logger.info(f"Connected to Redis: {redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            if REDIS_AVAILABLE:
                raise

    def is_allowed(
        self,
        client_id: str,
        capacity: int = 100,
        refill_rate: float = 10.0,
    ) -> Tuple[bool, int, int]:
        """
        Check if request is allowed under rate limit.

        Args:
            client_id: Unique client identifier
            capacity: Maximum tokens in bucket
            refill_rate: Tokens refilled per second

        Returns:
            Tuple of (allowed, remaining_tokens, reset_time_seconds)
        """
        if not self.redis:
            logger.warning("Redis not available, allowing all requests")
            return True, capacity, 0

        key = f"{self.key_prefix}{client_id}"
        now = time.time()

        try:
            # Get current bucket state
            bucket_data = self.redis.hgetall(key)

            if not bucket_data:
                # Initialize new bucket
                tokens = float(capacity) - 1.0
                self.redis.hset(
                    key,
                    mapping={
                        "tokens": tokens,
                        "last_refill": now,
                        "capacity": capacity,
                        "refill_rate": refill_rate,
                    },
                )
                self.redis.expire(key, int(capacity / max(refill_rate, 0.1)) + 60)
                return True, int(tokens), 0

            # Refill tokens
            tokens = float(bucket_data.get("tokens", capacity))
            last_refill = float(bucket_data.get("last_refill", now))
            bucket_capacity = int(bucket_data.get("capacity", capacity))
            bucket_refill_rate = float(bucket_data.get("refill_rate", refill_rate))

            elapsed = now - last_refill
            tokens = min(bucket_capacity, tokens + elapsed * bucket_refill_rate)

            # Try to consume token
            if tokens >= 1.0:
                tokens -= 1.0
                self.redis.hset(
                    key,
                    mapping={
                        "tokens": tokens,
                        "last_refill": now,
                    },
                )
                return True, int(tokens), 0
            else:
                # Calculate reset time
                reset_time = int(1.0 / bucket_refill_rate) if bucket_refill_rate > 0 else 60
                return False, 0, reset_time

        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return True, capacity, 0

    def get_quota(self, client_id: str) -> dict:
        """Get quota information for client.

        Args:
            client_id: Unique client identifier

        Returns:
            Dictionary with quota info
        """
        if not self.redis:
            return {"available": 0, "capacity": 0, "reset_time": 0}

        key = f"{self.key_prefix}{client_id}"

        try:
            bucket_data = self.redis.hgetall(key)
            if not bucket_data:
                return {"available": 0, "capacity": 0, "reset_time": 0}

            tokens = float(bucket_data.get("tokens", 0))
            capacity = int(bucket_data.get("capacity", 0))
            last_refill = float(bucket_data.get("last_refill", 0))
            refill_rate = float(bucket_data.get("refill_rate", 0))

            # Recalculate tokens with elapsed time
            elapsed = time.time() - last_refill
            tokens = min(capacity, tokens + elapsed * refill_rate)

            reset_time = int(1.0 / refill_rate) if refill_rate > 0 else 60

            return {
                "available": int(tokens),
                "capacity": capacity,
                "reset_time": reset_time,
            }
        except Exception as e:
            logger.error(f"Failed to get quota: {e}")
            return {"available": 0, "capacity": 0, "reset_time": 0}

    def reset(self, client_id: str) -> None:
        """Reset rate limit for client.

        Args:
            client_id: Unique client identifier
        """
        if not self.redis:
            return

        key = f"{self.key_prefix}{client_id}"
        try:
            self.redis.delete(key)
            logger.info(f"Reset rate limit for {client_id}")
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
