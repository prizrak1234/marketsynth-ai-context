"""Structured logging with structlog; PII must not appear in log output."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.core.config import Settings, get_settings
from app.security.pii import sanitize_payload


def sanitize_log_payload(payload: Any) -> Any:
    """Redact PII from arbitrary log payload values."""
    settings = get_settings()
    return sanitize_payload(payload, enabled=settings.pii_sanitizer_enabled)


def _sanitize_event_dict(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Processor: redact PII from all log event fields before emission."""
    for key, value in list(event_dict.items()):
        event_dict[key] = sanitize_log_payload(value)
    return event_dict


def configure_logging(settings: Settings) -> None:
    """Configure structlog + stdlib logging once at startup."""
    level = getattr(logging, settings.log_level, logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _sanitize_event_dict,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.is_development and settings.debug:
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name or "botfazer")
