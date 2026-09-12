"""Общие типы для детерминированных стратегий."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class Candle:
    ts: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class Signal:
    ts: int
    symbol: str
    strategy: str
    side: Literal["buy", "sell"]
    price: Decimal
    reason: str


class BaseStrategy(ABC):
    """Один интерфейс стратегии для бэктеста и paper-режима."""

    name: str

    @abstractmethod
    def on_candle(self, symbol: str, candle: Candle) -> Signal | None:
        """Обработать закрытую свечу и при необходимости вернуть сигнал."""

