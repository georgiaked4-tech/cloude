"""Рыночные данные через ccxt. Только публичные read-only эндпоинты.

Ордера не отправляются: приватные методы биржи здесь не используются вообще.
Биржа задаётся одной строкой в config.yaml (exchange.name).
"""

from __future__ import annotations

import time
from decimal import Decimal

import ccxt

from src.core.config import ExchangeConfig, MarketConfig
from src.core.log import get_logger
from src.strategy.base import Candle

log = get_logger(__name__)


def build_exchange(config: ExchangeConfig) -> ccxt.Exchange:
    """Создаёт клиент биржи без ключей — доступны только публичные данные."""
    exchange_class = getattr(ccxt, config.name, None)
    if exchange_class is None:
        raise ValueError(f"биржа {config.name} не поддерживается ccxt")
    exchange = exchange_class(
        {
            "enableRateLimit": True,
            "timeout": config.timeout_sec * 1000,
            "options": {"defaultType": config.market_type},
        }
    )
    return exchange


class MarketData:
    """Чтение свечей, тикеров и стакана. Никаких торговых операций."""

    def __init__(self, exchange_config: ExchangeConfig, market_config: MarketConfig) -> None:
        self.exchange_config = exchange_config
        self.market_config = market_config
        self.exchange = build_exchange(exchange_config)

    def _call_with_retry(self, func, *args, **kwargs):
        """Вызов с таймаутом, ретраями и обработкой rate limit.

        Задержка растёт экспоненциально: base, base*2, base*4. Максимум — max_retries попыток.
        """
        attempts = max(1, self.exchange_config.max_retries)
        # float здесь допустим: это длительность паузы для time.sleep, а не деньги.
        base_delay = float(self.exchange_config.retry_backoff_sec)
        last_error: Exception | None = None

        for attempt in range(attempts):
            try:
                return func(*args, **kwargs)
            except ccxt.RateLimitExceeded as error:
                last_error = error
                delay = base_delay * (2**attempt) * 2
                log.warning("rate_limit", attempt=attempt + 1, delay_sec=delay)
                time.sleep(delay)
            except (ccxt.NetworkError, ccxt.ExchangeNotAvailable, ccxt.RequestTimeout) as error:
                last_error = error
                delay = base_delay * (2**attempt)
                log.warning("network_error", attempt=attempt + 1, delay_sec=delay, error=str(error))
                time.sleep(delay)
        raise RuntimeError(f"не удалось получить данные после {attempts} попыток: {last_error}")

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str | None = None,
        since: int | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        """Свечи OHLCV. ts — миллисекунды UTC, значения — Decimal."""
        timeframe = timeframe or self.market_config.timeframe
        limit = limit or self.market_config.candles_limit
        raw = self._call_with_retry(self.exchange.fetch_ohlcv, symbol, timeframe, since, limit)
        return [
            Candle(
                ts=int(row[0]),
                open=Decimal(str(row[1])),
                high=Decimal(str(row[2])),
                low=Decimal(str(row[3])),
                close=Decimal(str(row[4])),
                volume=Decimal(str(row[5])),
            )
            for row in raw
        ]

    def fetch_last_price(self, symbol: str) -> Decimal:
        """Последняя цена из тикера."""
        ticker = self._call_with_retry(self.exchange.fetch_ticker, symbol)
        return Decimal(str(ticker["last"]))

    def fetch_order_book(self, symbol: str, limit: int = 20) -> dict:
        """Стакан. Цены и объёмы приводятся к Decimal."""
        book = self._call_with_retry(self.exchange.fetch_order_book, symbol, limit)
        return {
            "bids": [(Decimal(str(price)), Decimal(str(amount))) for price, amount in book["bids"]],
            "asks": [(Decimal(str(price)), Decimal(str(amount))) for price, amount in book["asks"]],
            "ts": int(book.get("timestamp") or 0),
        }
