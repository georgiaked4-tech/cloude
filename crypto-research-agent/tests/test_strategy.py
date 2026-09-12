from decimal import Decimal

from src.strategy.base import Candle
from src.strategy.ema_cross import EmaCrossStrategy


def candle(ts: int, close: str) -> Candle:
    value = Decimal(close)
    return Candle(ts, value, value, value, value, Decimal("1"))


def test_ema_strategy_is_deterministic() -> None:
    prices = ["3", "2", "1", "2", "4", "5"]
    first = EmaCrossStrategy(2, 3)
    second = EmaCrossStrategy(2, 3)
    first_signals = [first.on_candle("BTC/USDT", candle(i, p)) for i, p in enumerate(prices)]
    second_signals = [second.on_candle("BTC/USDT", candle(i, p)) for i, p in enumerate(prices)]
    assert first_signals == second_signals
    assert any(signal and signal.side == "buy" for signal in first_signals)

