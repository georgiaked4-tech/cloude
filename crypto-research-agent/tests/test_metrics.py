"""Тесты метрик бэктеста."""

from __future__ import annotations

from decimal import Decimal

from src.backtest.metrics import (
    compute_metrics,
    expectancy,
    format_report,
    max_drawdown_pct,
    profit_factor,
    win_rate_pct,
)
from src.paper.broker import Trade


def make_trade(pnl: str, fee: str = "1") -> Trade:
    """Закрытая сделка с заданным результатом."""
    net = Decimal(pnl)
    return Trade(
        symbol="BTC/USDT",
        side="long",
        qty=Decimal("1"),
        entry_price=Decimal("100"),
        entry_ts=0,
        exit_price=Decimal("100") + net,
        exit_ts=1,
        fee=Decimal(fee),
        pnl=net,
        pnl_pct=net,
        exit_reason="signal",
        gross_pnl=net + Decimal(fee),
    )


def test_max_drawdown() -> None:
    """Просадка считается от локального пика."""
    values = [Decimal("100"), Decimal("120"), Decimal("90"), Decimal("110")]
    # Пик 120, минимум после него 90: (120 - 90) / 120 * 100 = 25%.
    assert max_drawdown_pct(values) == Decimal("25")


def test_win_rate_and_profit_factor() -> None:
    """Win rate и profit factor считаются по PnL после комиссий."""
    trades = [make_trade("10"), make_trade("-5"), make_trade("15")]
    assert win_rate_pct(trades).quantize(Decimal("0.01")) == Decimal("66.67")
    assert profit_factor(trades) == Decimal("5")


def test_expectancy_matches_average_when_all_trades_counted() -> None:
    """Ожидание сделки равно среднему PnL."""
    trades = [make_trade("10"), make_trade("-5")]
    assert expectancy(trades) == Decimal("2.5")


def test_report_shows_gross_and_net() -> None:
    """Отчёт явно показывает результат до и после комиссий."""
    trades = [make_trade("10"), make_trade("-5")]
    metrics = compute_metrics(trades, [Decimal("10000"), Decimal("10005")], Decimal("10000"))
    assert metrics.total_fees == Decimal("2")
    assert metrics.gross_pnl == Decimal("7")
    assert metrics.net_pnl == Decimal("5")
    report = format_report(metrics, "BTC/USDT", "1h")
    assert "до комиссий" in report
    assert "после комиссий" in report


def test_losing_strategy_is_reported_as_losing() -> None:
    """Убыточный результат помечается явно, параметры не подгоняются."""
    equity = [Decimal("10000"), Decimal("9950")]
    metrics = compute_metrics([make_trade("-50")], equity, Decimal("10000"))
    assert "убыточна" in format_report(metrics, "BTC/USDT", "1h")
