"""Structured logging via structlog.

Production: JSON lines to stdout — ingested by any log aggregator.
Development: colored console output for readability.
"""
import logging
import sys

import structlog


def configure_logging(env: str = "development") -> None:
    """Configure structlog once at app startup."""
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if env == "production":
        processors = shared_processors + [
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )


def get_logger(component: str) -> structlog.stdlib.BoundLogger:
    """Return a logger pre-bound to a component name."""
    return structlog.get_logger().bind(component=component)
