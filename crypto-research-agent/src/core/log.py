"""Структурное логирование (structlog). Секреты маскируются на уровне процессора."""

from __future__ import annotations

import logging
import sys

import structlog

# Ключи, значения которых никогда не должны попасть в лог в открытом виде.
SECRET_KEYS = frozenset(
    {
        "anthropic_api_key",
        "api_key",
        "telegram_bot_token",
        "token",
        "secret",
        "password",
        "authorization",
    }
)
MASK = "***"


def mask_secrets(_logger: object, _method: str, event_dict: dict) -> dict:
    """Заменяет значения секретных ключей на маску."""
    for key in list(event_dict.keys()):
        if key.lower() in SECRET_KEYS:
            event_dict[key] = MASK
    return event_dict


def setup_logging(level: str = "INFO", json_output: bool = False) -> None:
    """Настраивает structlog один раз при старте процесса."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)
    if json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            mask_secrets,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Возвращает именованный логгер."""
    return structlog.get_logger(name)
