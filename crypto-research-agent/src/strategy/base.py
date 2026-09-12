"""Базовые типы стратегии. Один и тот же код используется в бэктесте и в paper-режиме."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

SIDE_BUY = "buy"
SIDE_SELL = "sell"


@dataclass(frozen=True)
class Candle:
    """Свеча. ts — миллисекунды UTC, цены и объём — Decimal."""

    ts: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @staticmethod
    def from_row(row: dict) -> Candle:
        """Создаёт свечу из строки таблицы candles."""
        return Candle(
            ts=int(row["ts"]),
            open=Decimal(row["open"]),
            high=Decimal(row["high"]),
            low=Decimal(row["low"]),
            close=Decimal(row["close"]),
            volume=Decimal(row["volume"]),
        )


@dataclass(frozen=True)
class Signal:
    """Торговый сигнал. Формируется только детерминированным кодом стратегии."""

    ts: int
    symbol: str
    side: str
    price: Decimal
    reason: str


class BaseStrategy(ABC):
    """Стратегия получает свечи по одной и возвращает сигнал или None.

    Состояние хранится внутри стратегии, поэтому бэктест и paper-режим
    вызывают ровно один и тот же метод update().
    """

    name: str = "base"

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    @property
    @abstractmethod
    def warmup(self) -> int:
        """Сколько свечей нужно до появления первого валидного сигнала."""

    @abstractmethod
    def update(self, candle: Candle) -> Signal | None:
        """Обрабатывает очередную свечу и возвращает сигнал, если он есть."""
