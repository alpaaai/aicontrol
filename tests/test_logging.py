"""Tests for structured logging configuration."""
import pytest
import structlog


def test_configure_logging_runs_without_error():
    """configure_logging must not raise."""
    from app.core.logging import configure_logging
    configure_logging(env="test")


def test_get_logger_returns_logger():
    """get_logger must return a usable logger."""
    from app.core.logging import configure_logging, get_logger
    configure_logging(env="test")
    logger = get_logger("test_component")
    assert logger is not None


def test_logger_has_bind_method():
    """Logger must support .bind() for context enrichment."""
    from app.core.logging import configure_logging, get_logger
    configure_logging(env="test")
    logger = get_logger("test_component")
    bound = logger.bind(request_id="abc123")
    assert bound is not None
