"""Structured logging setup. JSON output, contextual fields, request IDs."""
import logging
import sys

import structlog


def configure_logging(level: str = "INFO"):
    """Configure structlog to emit JSON logs to stdout."""

    # Standard library logging — used by uvicorn, FastAPI internals
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )

    # structlog config — what we use in our own code
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,        # request_id, etc.
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),            # the magic — emit JSON
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "forecast-api"):
    """Get a structured logger."""
    return structlog.get_logger(name)