"""
Quota management and billing tracking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class QuotaType(str, Enum):
    """Types of quotas."""

    API_CALLS = "api_calls"
    COMPUTE_SECONDS = "compute_seconds"
    STORAGE_GB = "storage_gb"
    BANDWIDTH_GB = "bandwidth_gb"


@dataclass
class QuotaLimit:
    """Quota limit definition."""

    quota_type: QuotaType
    limit: int
    period_seconds: int = 86400  # Daily by default
    warning_threshold: float = 0.8  # Warn at 80% usage

    def is_within_limit(self, current_usage: int) -> bool:
        """Check if usage is within limit."""
        return current_usage < self.limit

    def is_at_warning(self, current_usage: int) -> bool:
        """Check if usage is at warning threshold."""
        threshold = int(self.limit * self.warning_threshold)
        return current_usage >= threshold


@dataclass
class ClientQuota:
    """Client quota tracking."""

    client_id: str
    tier: str = "free"  # free, pro, enterprise
    quotas: Dict[QuotaType, QuotaLimit] = field(default_factory=dict)
    usage: Dict[QuotaType, int] = field(default_factory=dict)
    reset_time: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=1))
    billing_enabled: bool = False

    def get_remaining(self, quota_type: QuotaType) -> int:
        """Get remaining quota."""
        if quota_type not in self.quotas:
            return 0

        limit = self.quotas[quota_type].limit
        current = self.usage.get(quota_type, 0)
        return max(0, limit - current)

    def use_quota(self, quota_type: QuotaType, amount: int = 1) -> bool:
        """Deduct from quota.

        Args:
            quota_type: Type of quota to use
            amount: Amount to deduct

        Returns:
            True if quota available, False if exceeded
        """
        if quota_type not in self.quotas:
            return True  # No quota defined = unlimited

        current = self.usage.get(quota_type, 0)
        limit = self.quotas[quota_type].limit

        if current + amount > limit:
            logger.warning(
                f"Quota exceeded for {self.client_id}: "
                f"{quota_type}={current + amount}/{limit}"
            )
            return False

        self.usage[quota_type] = current + amount
        return True

    def is_at_limit(self, quota_type: QuotaType) -> bool:
        """Check if at limit."""
        if quota_type not in self.quotas:
            return False

        current = self.usage.get(quota_type, 0)
        return not self.quotas[quota_type].is_within_limit(current)

    def is_warning(self, quota_type: QuotaType) -> bool:
        """Check if at warning threshold."""
        if quota_type not in self.quotas:
            return False

        current = self.usage.get(quota_type, 0)
        return self.quotas[quota_type].is_at_warning(current)


# Default quotas per tier
DEFAULT_QUOTAS = {
    "free": {
        QuotaType.API_CALLS: QuotaLimit(QuotaType.API_CALLS, 1000),
        QuotaType.COMPUTE_SECONDS: QuotaLimit(QuotaType.COMPUTE_SECONDS, 3600),
    },
    "pro": {
        QuotaType.API_CALLS: QuotaLimit(QuotaType.API_CALLS, 100000),
        QuotaType.COMPUTE_SECONDS: QuotaLimit(QuotaType.COMPUTE_SECONDS, 86400),
    },
    "enterprise": {
        QuotaType.API_CALLS: QuotaLimit(QuotaType.API_CALLS, 10000000),
        QuotaType.COMPUTE_SECONDS: QuotaLimit(QuotaType.COMPUTE_SECONDS, 8640000),
    },
}
