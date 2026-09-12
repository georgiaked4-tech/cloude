"""Публичный read-only клиент рыночных данных CCXT."""

from __future__ import annotations

import time
from collections.abc import Callable
from decimal import Decimal
from typing import Any, TypeVar

import ccxt

from src.core.config import ExchangeConfig

T = TypeVar("T")


class MarketDataClient:
    """Получает публичные свечи, тикеры и стакан без API-ключей."""

    def __init__(self, config: ExchangeConfig) -> None:
        exchange_type = getattr(ccxt, config.name, None)
        if exchange_type is None:
            raise ValueError(f"Биржа {config.name!r} не поддерживается CCXT")
        self.config = config
        self.exchange = exchange_type(
            {"enableRateLimit": True, "timeout": config.timeout_ms}
        )

    def _with_retry(self, operation: Callable[[], T]) -> T:
        """Повторить сетевой вызов максимум три раза с экспоненциальной паузой."""

        for attempt in range(self.config.max_retries):
            try:
                return operation()
            except (ccxt.RateLimitExceeded, ccxt.NetworkError, ccxt.ExchangeNotAvailable):
                if attempt + 1 >= self.config.max_retries:
                    raise
                delay = self.config.retry_base_seconds * (Decimal(2) ** attempt)
                time.sleep(float(delay))
        raise RuntimeError("Недостижимая ветка retry")

    def fetch_ohlcv(
        self, symbol: str, timeframe: str, limit: int = 500, since: int | None = None
    ) -> list[tuple[int, Decimal, Decimal, Decimal, Decimal, Decimal]]:
        """Получить OHLCV и сразу преобразовать числа в Decimal через строки."""

        raw = self._with_retry(
            lambda: self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        )
        return [
            (
                int(row[0]),
                Decimal(str(row[1])),
                Decimal(str(row[2])),
                Decimal(str(row[3])),
                Decimal(str(row[4])),
                Decimal(str(row[5])),
            )
            for row in raw
        ]

    def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        """Получить публичный тикер без приватных реквизитов."""

        return self._with_retry(lambda: self.exchange.fetch_ticker(symbol))

    def fetch_order_book(self, symbol: str, limit: int = 50) -> dict[str, Any]:
        """Получить публичный стакан без возможности выставить заявку."""

        return self._with_retry(lambda: self.exchange.fetch_order_book(symbol, limit))

