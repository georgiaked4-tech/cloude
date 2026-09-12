"""Референсная стратегия пересечения двух EMA."""

from __future__ import annotations

from decimal import Decimal

from src.strategy.base import BaseStrategy, Candle, Signal


class EmaCrossStrategy(BaseStrategy):
    """Формирует buy/sell только в момент подтверждённого пересечения EMA."""

    name = "ema_cross"

    def __init__(self, fast_period: int, slow_period: int) -> None:
        if fast_period <= 0 or slow_period <= fast_period:
            raise ValueError("Периоды должны удовлетворять 0 < fast < slow")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.fast_ema: Decimal | None = None
        self.slow_ema: Decimal | None = None
        self.previous_relation: int | None = None
        self.seen = 0

    @staticmethod
    def _next_ema(previous: Decimal | None, price: Decimal, period: int) -> Decimal:
        """EMA = цена×α + предыдущая EMA×(1−α), где α=2/(период+1)."""

        if previous is None:
            return price
        alpha = Decimal(2) / Decimal(period + 1)
        return price * alpha + previous * (Decimal(1) - alpha)

    def on_candle(self, symbol: str, candle: Candle) -> Signal | None:
        """Обновить EMA и вернуть сигнал лишь после прогрева slow_period свечей."""

        self.seen += 1
        self.fast_ema = self._next_ema(self.fast_ema, candle.close, self.fast_period)
        self.slow_ema = self._next_ema(self.slow_ema, candle.close, self.slow_period)
        if self.fast_ema > self.slow_ema:
            relation = 1
        elif self.fast_ema < self.slow_ema:
            relation = -1
        else:
            relation = 0

        if self.seen < self.slow_period:
            self.previous_relation = relation
            return None

        previous = self.previous_relation
        self.previous_relation = relation
        if previous is not None and previous <= 0 < relation:
            return Signal(
                candle.ts, symbol, self.name, "buy", candle.close,
                "Быстрая EMA пересекла медленную снизу вверх",
            )
        if previous is not None and previous >= 0 > relation:
            return Signal(
                candle.ts, symbol, self.name, "sell", candle.close,
                "Быстрая EMA пересекла медленную сверху вниз",
            )
        return None
