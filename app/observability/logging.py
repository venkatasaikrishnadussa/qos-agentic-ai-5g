from __future__ import annotations

import logging
import sys
from typing import Any, Dict

import structlog

from app.config.settings import settings


def _get_structlog_processors() -> list[structlog.types.Processor]:
    return [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]


def configure_logging() -> None:
    """
    Configure structured logging for the entire application.
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=_get_structlog_processors(),
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger bound with the service name.
    """
    logger = structlog.get_logger(name)
    return logger.bind(service=settings.service_name)


def log_exception(
    logger: structlog.stdlib.BoundLogger, msg: str, **kwargs: Dict[str, Any]
) -> None:
    logger.error(msg, exc_info=True, **kwargs)


