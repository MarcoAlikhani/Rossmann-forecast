"""Custom middleware: request IDs, latency tracking, metrics."""

import time
import uuid

import structlog
from fastapi import Request
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger("forecast-api")


# Prometheus metrics — collected per request
REQUEST_COUNT = Counter(
    "forecast_api_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "forecast_api_request_duration_seconds",
    "Request latency in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

PREDICTION_COUNT = Counter(
    "forecast_api_predictions_total",
    "Total predictions made",
    labelnames=["endpoint"],
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request ID, logs request start/end, records metrics."""

    async def dispatch(self, request: Request, call_next):
        # Use client-provided ID if present (for distributed tracing), else generate
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Bind request_id to all log lines emitted during this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        logger.info("request_started")

        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            duration = time.perf_counter() - start
            logger.exception("request_failed", duration_s=duration)
            REQUEST_COUNT.labels(
                method=request.method, endpoint=request.url.path, status_code="500"
            ).inc()
            REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(
                duration
            )
            raise

        duration = time.perf_counter() - start
        logger.info("request_completed", status_code=status, duration_s=round(duration, 4))

        REQUEST_COUNT.labels(
            method=request.method, endpoint=request.url.path, status_code=str(status)
        ).inc()
        REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(duration)

        # Echo request ID back to the client for distributed debugging
        response.headers["X-Request-ID"] = request_id
        return response
