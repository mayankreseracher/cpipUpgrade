"""
Billing event tracking for metered usage.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class BillingEventType(str, Enum):
    """Types of billable events."""

    API_CALL = "api_call"
    COMPUTE_SECOND = "compute_second"
    STORAGE_GB_DAY = "storage_gb_day"
    BANDWIDTH_GB = "bandwidth_gb"


@dataclass
class BillingEvent:
    """Billable event record."""

    event_type: BillingEventType
    client_id: str
    amount: float
    unit_price: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    description: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def total_cost(self) -> float:
        """Calculate total cost."""
        return self.amount * self.unit_price


class BillingTracker:
    """Track and aggregate billing events."""

    def __init__(
        self,
        pricing: Optional[dict] = None,
    ):
        """
        Initialize billing tracker.

        Args:
            pricing: Dict mapping BillingEventType to unit price
        """
        self.pricing = pricing or {
            BillingEventType.API_CALL: 0.0001,  # $0.0001 per call
            BillingEventType.COMPUTE_SECOND: 0.01,  # $0.01 per second
            BillingEventType.STORAGE_GB_DAY: 0.05,  # $0.05 per GB-day
            BillingEventType.BANDWIDTH_GB: 0.1,  # $0.1 per GB
        }
        self.events: List[BillingEvent] = []

    def record_event(
        self,
        event_type: BillingEventType,
        client_id: str,
        amount: float,
        description: str = "",
        metadata: Optional[dict] = None,
    ) -> BillingEvent:
        """
        Record a billable event.

        Args:
            event_type: Type of event
            client_id: Client ID
            amount: Quantity
            description: Human-readable description
            metadata: Additional metadata

        Returns:
            BillingEvent that was recorded
        """
        unit_price = self.pricing.get(event_type, 0.0)

        event = BillingEvent(
            event_type=event_type,
            client_id=client_id,
            amount=amount,
            unit_price=unit_price,
            description=description,
            metadata=metadata or {},
        )

        self.events.append(event)
        logger.info(
            f"Recorded billing event: {event_type} for {client_id}: "
            f"{amount} x ${unit_price} = ${event.total_cost}"
        )

        return event

    def get_client_usage(
        self,
        client_id: str,
        event_type: Optional[BillingEventType] = None,
    ) -> dict:
        """
        Get usage summary for client.

        Args:
            client_id: Client ID
            event_type: Optional filter by event type

        Returns:
            Usage summary dictionary
        """
        client_events = [
            e for e in self.events if e.client_id == client_id
        ]

        if event_type:
            client_events = [
                e for e in client_events if e.event_type == event_type
            ]

        total_cost = sum(e.total_cost for e in client_events)
        total_amount = sum(e.amount for e in client_events)

        return {
            "client_id": client_id,
            "event_count": len(client_events),
            "total_amount": total_amount,
            "total_cost": total_cost,
            "events_by_type": self._group_by_type(client_events),
        }

    def _group_by_type(self, events: List[BillingEvent]) -> dict:
        """Group events by type."""
        result = {}
        for event in events:
            if event.event_type not in result:
                result[event.event_type] = {
                    "count": 0,
                    "total_amount": 0,
                    "total_cost": 0,
                }
            result[event.event_type]["count"] += 1
            result[event.event_type]["total_amount"] += event.amount
            result[event.event_type]["total_cost"] += event.total_cost

        return result
