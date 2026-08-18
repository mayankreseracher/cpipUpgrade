"""
Custom span attributes and helpers for cpip.
"""

from typing import Optional, Any, Dict
from opentelemetry import trace


class SpanAttributes:
    """Standard span attribute names for cpip."""

    # Request
    HTTP_METHOD = "http.method"
    HTTP_URL = "http.url"
    HTTP_STATUS_CODE = "http.status_code"
    HTTP_CLIENT_IP = "http.client_ip"

    # Device
    DEVICE_ID = "device.id"
    DEVICE_PLATFORM = "device.platform"

    # Offload
    OFFLOAD_PACKAGE = "offload.package"
    OFFLOAD_DURATION_MS = "offload.duration_ms"
    OFFLOAD_CACHE_HIT = "offload.cache_hit"
    OFFLOAD_CLOUD_TIME_MS = "offload.cloud_time_ms"

    # Build
    BUILD_ID = "build.id"
    BUILD_STATUS = "build.status"
    BUILD_ARTIFACT_SIZE = "build.artifact_size_bytes"

    # Database
    DB_QUERY = "db.query"
    DB_ROWS_AFFECTED = "db.rows_affected"


def set_span_attributes(span: trace.Span, attributes: Dict[str, Any]) -> None:
    """
    Set multiple attributes on a span.

    Args:
        span: OpenTelemetry span
        attributes: Dictionary of attribute key-value pairs
    """
    if not span or not span.is_recording():
        return

    for key, value in attributes.items():
        if value is not None:
            try:
                span.set_attribute(key, value)
            except Exception as e:
                # Log but don't fail on attribute setting errors
                pass


def record_span_event(
    span: trace.Span,
    event_name: str,
    attributes: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Record an event within a span.

    Args:
        span: OpenTelemetry span
        event_name: Event name
        attributes: Optional event attributes
    """
    if not span or not span.is_recording():
        return

    try:
        span.add_event(event_name, attributes or {})
    except Exception as e:
        pass
