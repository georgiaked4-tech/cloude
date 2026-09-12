"""Структурное логирование с маскированием секретоподобных полей."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

_SENSITIVE_PARTS = ("token", "secret", "password", "api_key")


def mask_secrets(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Скрыть значения полей, название которых похоже на секрет."""

    for key in list(event_dict):
        if any(part in key.lower() for part in _SENSITIVE_PARTS):
            event_dict[key] = "***"
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    """Настроить JSON-логи на stdout."""

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper())
    structlog.configure(
        processors=[
            mask_secrets,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
    )


def get_logger() -> Any:
    """Вернуть настроенный структурный логгер."""

    return structlog.get_logger()

