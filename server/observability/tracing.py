"""
OpenTelemetry tracing instrumentation for cpip.

Provides distributed tracing for HTTP requests, database operations,
and external service calls.
"""

from __future__ import annotations

import logging
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

logger = logging.getLogger(__name__)


class TracingConfig:
    """OpenTelemetry tracing configuration."""

    def __init__(
        self,
        enabled: bool = False,
        otlp_endpoint: str = "http://localhost:4317",
        service_name: str = "cpip-server",
        service_version: str = "0.1.0",
        environment: str = "development",
        sample_rate: float = 1.0,
    ):
        """
        Initialize tracing configuration.

        Args:
            enabled: Enable OpenTelemetry tracing
            otlp_endpoint: OTLP collector endpoint (gRPC)
            service_name: Service name for traces
            service_version: Service version
            environment: Environment name (development, staging, production)
            sample_rate: Trace sampling rate (0.0-1.0)
        """
        self.enabled = enabled
        self.otlp_endpoint = otlp_endpoint
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
        self.sample_rate = max(0.0, min(1.0, sample_rate))

        self.tracer_provider: Optional[TracerProvider] = None
        self.meter_provider: Optional[MeterProvider] = None

    def initialize(self) -> None:
        """
        Initialize OpenTelemetry providers and exporters.

        Must be called before using tracing in the application.
        """
        if not self.enabled:
            logger.debug("OpenTelemetry tracing is disabled")
            return

        try:
            # Create resource with service metadata
            resource = Resource.create(
                {
                    "service.name": self.service_name,
                    "service.version": self.service_version,
                    "deployment.environment": self.environment,
                }
            )

            # Initialize trace provider with OTLP exporter
            trace_exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint)
            self.tracer_provider = TracerProvider(resource=resource)
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(trace_exporter)
            )
            trace.set_tracer_provider(self.tracer_provider)
            logger.info(f"Trace provider initialized: endpoint={self.otlp_endpoint}")

            # Initialize metrics provider with OTLP exporter
            metric_exporter = OTLPMetricExporter(endpoint=self.otlp_endpoint)
            metric_reader = PeriodicExportingMetricReader(metric_exporter)
            self.meter_provider = MeterProvider(
                resource=resource, metric_readers=[metric_reader]
            )
            metrics.set_meter_provider(self.meter_provider)
            logger.info(f"Meter provider initialized: endpoint={self.otlp_endpoint}")

        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}")
            if not self.enabled:
                logger.warning("Continuing without tracing")
            else:
                raise

    def instrument_fastapi(self, app) -> None:
        """
        Instrument FastAPI application with automatic tracing.

        Args:
            app: FastAPI application instance
        """
        if not self.enabled or not self.tracer_provider:
            logger.debug("Skipping FastAPI instrumentation (tracing disabled)")
            return

        try:
            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=self.tracer_provider,
            )
            logger.info("FastAPI instrumented for distributed tracing")
        except Exception as e:
            logger.error(f"Failed to instrument FastAPI: {e}")

    def instrument_sqlalchemy(self) -> None:
        """
        Instrument SQLAlchemy for database operation tracing.
        """
        if not self.enabled or not self.tracer_provider:
            logger.debug("Skipping SQLAlchemy instrumentation (tracing disabled)")
            return

        try:
            SQLAlchemyInstrumentor().instrument(tracer_provider=self.tracer_provider)
            logger.info("SQLAlchemy instrumented for database tracing")
        except Exception as e:
            logger.error(f"Failed to instrument SQLAlchemy: {e}")

    def instrument_requests(self) -> None:
        """
        Instrument requests library for HTTP client tracing.
        """
        if not self.enabled or not self.tracer_provider:
            logger.debug("Skipping requests instrumentation (tracing disabled)")
            return

        try:
            RequestsInstrumentor().instrument(tracer_provider=self.tracer_provider)
            logger.info("requests library instrumented for HTTP client tracing")
        except Exception as e:
            logger.error(f"Failed to instrument requests: {e}")

    def instrument_httpx(self) -> None:
        """
        Instrument httpx library for async HTTP client tracing.
        """
        if not self.enabled or not self.tracer_provider:
            logger.debug("Skipping httpx instrumentation (tracing disabled)")
            return

        try:
            HTTPXClientInstrumentor().instrument(tracer_provider=self.tracer_provider)
            logger.info("httpx library instrumented for async HTTP client tracing")
        except Exception as e:
            logger.error(f"Failed to instrument httpx: {e}")

    def instrument_all(self, app=None) -> None:
        """
        Instrument all supported libraries.

        Args:
            app: FastAPI application instance (optional)
        """
        if not self.enabled:
            logger.debug("OpenTelemetry instrumentation skipped (tracing disabled)")
            return

        self.instrument_sqlalchemy()
        self.instrument_requests()
        self.instrument_httpx()
        if app:
            self.instrument_fastapi(app)

    def get_tracer(self, name: str) -> trace.Tracer:
        """
        Get a tracer instance.

        Args:
            name: Module name for the tracer

        Returns:
            Tracer instance
        """
        if not self.tracer_provider:
            return trace.get_tracer(name)
        return self.tracer_provider.get_tracer(name)

    def get_meter(self, name: str) -> metrics.Meter:
        """
        Get a meter instance.

        Args:
            name: Module name for the meter

        Returns:
            Meter instance
        """
        if not self.meter_provider:
            return metrics.get_meter(name)
        return self.meter_provider.get_meter(name)

    def shutdown(self) -> None:
        """
        Gracefully shutdown tracing providers.
        """
        if not self.enabled:
            return

        try:
            if self.tracer_provider:
                self.tracer_provider.force_flush(timeout_millis=5000)
            if self.meter_provider:
                self.meter_provider.force_flush(timeout_millis=5000)
            logger.info("OpenTelemetry providers shut down successfully")
        except Exception as e:
            logger.error(f"Error during OpenTelemetry shutdown: {e}")
