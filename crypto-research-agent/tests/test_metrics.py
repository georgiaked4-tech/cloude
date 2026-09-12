from decimal import Decimal

import pytest

from src.backtest.metrics import calculate_metrics
from src.core.timeframe import periods_per_year, timeframe_ms
from src.paper.broker import PaperTrade


def trade(pnl: str, fee: str = "0.2") -> PaperTrade:
    value = Decimal(pnl)
    return PaperTrade(
        1, "BTC/USDT", "long", Decimal("1"), Decimal("100"), 1,
        Decimal("101"), 2, Decimal(fee), value, value, "take_profit",
    )


def test_periods_per_year_follows_timeframe() -> None:
    assert periods_per_year("1h") == Decimal(365 * 24)
    assert periods_per_year("1d") == Decimal(365)
    assert periods_per_year("15m") == Decimal(365 * 24 * 4)
    assert timeframe_ms("1h") == 3_600_000


def test_unknown_timeframe_is_rejected() -> None:
    with pytest.raises(ValueError):
        periods_per_year("1y")
    with pytest.raises(ValueError):
        periods_per_year("0h")


def test_sharpe_scales_with_bar_length() -> None:
    equity = [Decimal("100"), Decimal("101"), Decimal("102"), Decimal("104")]
    trades = [trade("1")]
    hourly = calculate_metrics(trades, equity, Decimal("100"), "1h").sharpe
    daily = calculate_metrics(trades, equity, Decimal("100"), "1d").sharpe
    # Часовых баров в году в 24 раза больше, значит множитель отличается в √24.
    assert hourly > daily
    assert (hourly / daily) ** 2 == pytest.approx(24, rel=Decimal("0.0001"))


def test_report_separates_result_before_and_after_fees() -> None:
    metrics = calculate_metrics(
        [trade("1", "0.5"), trade("-2", "0.5")], [Decimal("100")], Decimal("100"), "1h"
    )
    assert metrics.total_fees == Decimal("1.0")
    assert metrics.total_return_after_fees_pct == Decimal("-1")
    assert metrics.total_return_before_fees_pct == Decimal("0")
    assert metrics.expectancy == metrics.average_trade
    assert metrics.trades == 2
