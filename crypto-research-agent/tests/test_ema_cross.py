"""Тесты стратегии EMA-пересечения."""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.strategy.base import SIDE_BUY, SIDE_SELL, Candle
from src.strategy.ema_cross import EmaCrossStrategy, ema_next


def make_candle(ts: int, close: str) -> Candle:
    """Свеча с одинаковыми ценами, кроме заданного закрытия."""
    price = Decimal(close)
    return Candle(ts=ts, open=price, high=price, low=price, close=price, volume=Decimal("1"))


def test_ema_first_value_equals_price() -> None:
    """Без предыдущего значения EMA стартует с текущей цены."""
    assert ema_next(None, Decimal("100"), 10) == Decimal("100")


def test_ema_moves_towards_price() -> None:
    """EMA движется в сторону новой цены, но не достигает её за один шаг."""
    value = ema_next(Decimal("100"), Decimal("110"), 9)
    assert Decimal("100") < value < Decimal("110")


def test_fast_period_must_be_smaller() -> None:
    """Быстрый период не может быть больше медленного."""
    with pytest.raises(ValueError):
        EmaCrossStrategy("BTC/USDT", fast_period=26, slow_period=12)


def test_no_signal_during_warmup() -> None:
    """До прогрева сигналов нет."""
    strategy = EmaCrossStrategy("BTC/USDT", fast_period=2, slow_period=4)
    signals = [strategy.update(make_candle(i, "100")) for i in range(4)]
    assert all(signal is None for signal in signals)


def test_buy_then_sell_on_crossovers() -> None:
    """Рост даёт сигнал на покупку, последующее падение — на выход."""
    strategy = EmaCrossStrategy("BTC/USDT", fast_period=2, slow_period=4)
    for i in range(6):
        strategy.update(make_candle(i, "100"))

    buy = None
    for i, price in enumerate(["110", "120", "130"], start=6):
        buy = strategy.update(make_candle(i, price)) or buy
    assert buy is not None and buy.side == SIDE_BUY

    sell = None
    for i, price in enumerate(["90", "80", "70", "60"], start=9):
        sell = strategy.update(make_candle(i, price)) or sell
    assert sell is not None and sell.side == SIDE_SELL
