"""
Observability module for tracing, metrics, and logging.
"""

from server.observability.tracing import TracingConfig
from server.observability.spans import SpanAttributes, set_span_attributes, record_span_event

__all__ = [
    "TracingConfig",
    "SpanAttributes",
    "set_span_attributes",
    "record_span_event",
]
