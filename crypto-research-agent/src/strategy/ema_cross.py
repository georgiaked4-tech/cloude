"""Референсная стратегия: пересечение двух EMA. Логика полностью детерминированная."""

from __future__ import annotations

from decimal import Decimal

from src.strategy.base import SIDE_BUY, SIDE_SELL, BaseStrategy, Candle, Signal


def ema_next(previous: Decimal | None, price: Decimal, period: int) -> Decimal:
    """Следующее значение EMA.

    Формула: EMA_t = price_t * k + EMA_(t-1) * (1 - k), где k = 2 / (period + 1).
    Если предыдущего значения нет, EMA стартует с текущей цены.
    """
    if previous is None:
        return price
    k = Decimal(2) / Decimal(period + 1)
    return price * k + previous * (Decimal(1) - k)


class EmaCrossStrategy(BaseStrategy):
    """Покупка при пересечении быстрой EMA снизу вверх, выход — при обратном пересечении."""

    name = "ema_cross"

    def __init__(self, symbol: str, fast_period: int = 12, slow_period: int = 26) -> None:
        super().__init__(symbol)
        if fast_period >= slow_period:
            raise ValueError("fast_period должен быть меньше slow_period")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self._fast: Decimal | None = None
        self._slow: Decimal | None = None
        self._prev_diff: Decimal | None = None
        self._seen = 0

    @property
    def warmup(self) -> int:
        """До прогрева медленной EMA сигналы не выдаются."""
        return self.slow_period

    def update(self, candle: Candle) -> Signal | None:
        """Обновляет обе EMA и возвращает сигнал в момент пересечения."""
        self._seen += 1
        self._fast = ema_next(self._fast, candle.close, self.fast_period)
        self._slow = ema_next(self._slow, candle.close, self.slow_period)
        diff = self._fast - self._slow
        prev_diff = self._prev_diff
        self._prev_diff = diff

        if self._seen <= self.warmup or prev_diff is None:
            return None

        # Пересечение снизу вверх: быстрая EMA была ниже медленной, стала выше.
        if prev_diff <= 0 < diff:
            return Signal(
                ts=candle.ts,
                symbol=self.symbol,
                side=SIDE_BUY,
                price=candle.close,
                reason=f"EMA{self.fast_period} пересекла EMA{self.slow_period} снизу вверх",
            )
        # Пересечение сверху вниз: сигнал на закрытие длинной позиции.
        if prev_diff >= 0 > diff:
            return Signal(
                ts=candle.ts,
                symbol=self.symbol,
                side=SIDE_SELL,
                price=candle.close,
                reason=f"EMA{self.fast_period} пересекла EMA{self.slow_period} сверху вниз",
            )
        return None


def build_strategy(symbol: str, params: dict[str, int]) -> EmaCrossStrategy:
    """Фабрика стратегии из параметров конфига."""
    return EmaCrossStrategy(
        symbol=symbol,
        fast_period=int(params.get("fast_period", 12)),
        slow_period=int(params.get("slow_period", 26)),
    )
