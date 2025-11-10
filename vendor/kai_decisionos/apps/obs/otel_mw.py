from __future__ import annotations

import logging
import os
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, Request
from starlette.responses import Response

from pkg.context import corr as corr_ctx
from pkg.context import trace as trace_ctx

try:
    from opentelemetry import trace
    from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    _OTEL_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    trace = None  # type: ignore
    OpenTelemetryMiddleware = None  # type: ignore
    TracerProvider = None  # type: ignore
    BatchSpanProcessor = None  # type: ignore
    OTLPSpanExporter = None  # type: ignore
    Resource = None  # type: ignore
    SERVICE_NAME = "service.name"  # type: ignore
    _OTEL_AVAILABLE = False


LOGGER = logging.getLogger("obs.otel")


def build_tracer_provider(service_name: str, endpoint: str | None = None) -> Optional["TracerProvider"]:
    """Construct an OTLP-enabled tracer provider if dependencies are available."""
    if not _OTEL_AVAILABLE:
        LOGGER.warning("OpenTelemetry SDK not available; skip tracer init")
        return None

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    if endpoint:
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=endpoint.startswith("http://"))
    else:
        exporter = OTLPSpanExporter()
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    return provider


def install_otel_middleware(
    app: FastAPI,
    service_name: str = "decisionos-gateway",
    collector_endpoint: str | None = None,
    capture_corr_header: str = "X-Corr-Id",
) -> None:
    """Install OTel ASGI middleware and inject trace/corr information on every request."""
    provider = None
    if _OTEL_AVAILABLE:
        provider = build_tracer_provider(service_name, collector_endpoint)
        if provider and OpenTelemetryMiddleware:
            LOGGER.info("Installing OpenTelemetry middleware (service=%s)", service_name)
            app.add_middleware(OpenTelemetryMiddleware)
    else:
        LOGGER.info("OpenTelemetry packages missing; middleware acts as noop")

    @app.middleware("http")
    async def _obs_context(request: Request, call_next: Callable[[Request], Any]) -> Response:  # type: ignore[override]
        incoming_corr = (
            request.headers.get(capture_corr_header)
            or request.headers.get("X-Correlation-Id")
        )
        if incoming_corr:
            corr_ctx.set_corr_id(incoming_corr)
        else:
            corr_ctx.ensure_corr_id()

        # Ensure trace context for logging even if OTel disabled
        if _OTEL_AVAILABLE and trace:
            span = trace.get_current_span()
            ctx_trace_id = span.get_span_context().trace_id
            if ctx_trace_id:
                trace_ctx.set_trace_hex(f"{ctx_trace_id:032x}")
            else:
                trace_ctx.ensure_trace()
        else:
            trace_ctx.ensure_trace()

        response: Response = await call_next(request)
        response.headers[capture_corr_header] = corr_ctx.get_corr_id()
        if _OTEL_AVAILABLE and trace:
            span = trace.get_current_span()
            ctx_trace_id = span.get_span_context().trace_id
            if ctx_trace_id:
                response.headers["X-Trace-Id"] = f"{ctx_trace_id:032x}"
        else:
            response.headers.setdefault("X-Trace-Id", trace_ctx.get_trace_id())
        return response

    if provider:
        LOGGER.info("OTel tracer provider active with processor=%s", provider._active_span_processor.__class__.__name__)  # type: ignore[attr-defined]


def install_from_env(app: FastAPI) -> None:
    """Helper to install middleware using environment variables."""
    service_name = os.getenv("OBS_SERVICE_NAME", "decisionos-gateway")
    endpoint = os.getenv("OBS_OTLP_ENDPOINT")
    install_otel_middleware(app, service_name=service_name, collector_endpoint=endpoint)
