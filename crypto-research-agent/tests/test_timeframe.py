import pytest

from src.core.timeframe import is_closed, timeframe_minutes, timeframe_ms

HOUR = timeframe_ms("1h")


def test_forming_candle_is_not_closed() -> None:
    opened_at = 1_700_000_000_000
    # Свеча закрывается ровно через час после открытия.
    assert is_closed(opened_at, "1h", opened_at + HOUR) is True
    assert is_closed(opened_at, "1h", opened_at + HOUR - 1) is False


def test_only_finished_candles_survive_the_filter() -> None:
    now = 1_700_000_000_000
    timestamps = [now - 3 * HOUR, now - 2 * HOUR, now - HOUR, now]
    closed = [ts for ts in timestamps if is_closed(ts, "1h", now)]
    assert closed == timestamps[:3]


def test_month_is_rejected_instead_of_read_as_a_minute() -> None:
    # В CCXT "1M" — месяц; приведение к нижнему регистру сделало бы из него минуту.
    with pytest.raises(ValueError):
        timeframe_minutes("1M")
    with pytest.raises(ValueError):
        timeframe_minutes("1H")
    assert timeframe_minutes("1m") == 1
