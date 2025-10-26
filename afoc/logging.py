"""Structured logging helpers with graceful structlog fallback."""

from __future__ import annotations

import logging
from typing import Any

try:  # pragma: no cover - optional dependency
    import structlog
except Exception:  # pragma: no cover - fallback when structlog absent
    structlog = None  # type: ignore


_configured = False


def configure_logging(level: int = logging.INFO, json: bool = False) -> None:
    """Initialise logging configuration once."""

    global _configured
    if _configured:
        return
    if structlog is None:
        logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    else:  # pragma: no cover - configuration exercised via runtime usage
        processors: list[Any] = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]
        if json:
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer())
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(level),
            processors=processors,
        )
    _configured = True


def get_logger(name: str) -> Any:
    """Return a structlog or stdlib logger depending on availability."""

    if structlog is not None:
        configure_logging()
        return structlog.get_logger(name)
    configure_logging()
    return logging.getLogger(name)
