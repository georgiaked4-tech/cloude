"""Метрики бэктеста. Отчёт всегда показывает результат до и после комиссий."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.paper.broker import Trade

HUNDRED = Decimal("100")


@dataclass(frozen=True)
class Metrics:
    """Полный набор метрик по списку сделок и кривой капитала."""

    trades_count: int
    total_return_pct: Decimal
    total_return_pct_gross: Decimal
    net_pnl: Decimal
    gross_pnl: Decimal
    total_fees: Decimal
    max_drawdown_pct: Decimal
    sharpe: Decimal
    win_rate_pct: Decimal
    profit_factor: Decimal
    expectancy: Decimal
    average_trade: Decimal


def total_pnl(trades: list[Trade]) -> tuple[Decimal, Decimal, Decimal]:
    """Суммарный PnL до комиссий, после комиссий и сумма комиссий."""
    gross = sum((trade.gross_pnl for trade in trades), Decimal("0"))
    fees = sum((trade.fee for trade in trades), Decimal("0"))
    net = sum((trade.pnl for trade in trades), Decimal("0"))
    return gross, net, fees


def max_drawdown_pct(equity_values: list[Decimal]) -> Decimal:
    """Максимальная просадка капитала в процентах.

    Формула: max по всем точкам от (пик - текущее значение) / пик * 100.
    """
    if not equity_values:
        return Decimal("0")
    peak = equity_values[0]
    max_dd = Decimal("0")
    for value in equity_values:
        if value > peak:
            peak = value
        if peak > 0:
            drawdown = (peak - value) / peak * HUNDRED
            if drawdown > max_dd:
                max_dd = drawdown
    return max_dd


def sharpe_ratio(equity_values: list[Decimal], periods_per_year: int = 365 * 24) -> Decimal:
    """Коэффициент Шарпа по доходностям кривой капитала (безрисковая ставка = 0).

    Формула: среднее доходностей / стандартное отклонение * sqrt(число периодов в году).
    """
    if len(equity_values) < 3:
        return Decimal("0")
    returns: list[Decimal] = []
    for previous, current in zip(equity_values, equity_values[1:], strict=False):
        if previous > 0:
            returns.append((current - previous) / previous)
    if len(returns) < 2:
        return Decimal("0")
    mean = sum(returns, Decimal("0")) / Decimal(len(returns))
    variance = sum(((r - mean) ** 2 for r in returns), Decimal("0")) / Decimal(len(returns) - 1)
    if variance <= 0:
        return Decimal("0")
    return mean / variance.sqrt() * Decimal(periods_per_year).sqrt()


def win_rate_pct(trades: list[Trade]) -> Decimal:
    """Доля прибыльных сделок после комиссий, в процентах."""
    if not trades:
        return Decimal("0")
    wins = sum(1 for trade in trades if trade.pnl > 0)
    return Decimal(wins) / Decimal(len(trades)) * HUNDRED


def profit_factor(trades: list[Trade]) -> Decimal:
    """Отношение суммы прибылей к сумме убытков (по модулю).

    Если убытков нет, возвращается 0 как признак неопределённости.
    """
    profits = sum((trade.pnl for trade in trades if trade.pnl > 0), Decimal("0"))
    losses = sum((-trade.pnl for trade in trades if trade.pnl < 0), Decimal("0"))
    if losses <= 0:
        return Decimal("0")
    return profits / losses


def expectancy(trades: list[Trade]) -> Decimal:
    """Математическое ожидание сделки.

    Формула: доля выигрышей * средний выигрыш - доля проигрышей * средний проигрыш.
    """
    if not trades:
        return Decimal("0")
    wins = [trade.pnl for trade in trades if trade.pnl > 0]
    losses = [-trade.pnl for trade in trades if trade.pnl < 0]
    count = Decimal(len(trades))
    win_share = Decimal(len(wins)) / count
    loss_share = Decimal(len(losses)) / count
    avg_win = (sum(wins, Decimal("0")) / Decimal(len(wins))) if wins else Decimal("0")
    avg_loss = (sum(losses, Decimal("0")) / Decimal(len(losses))) if losses else Decimal("0")
    return win_share * avg_win - loss_share * avg_loss


def compute_metrics(
    trades: list[Trade], equity_values: list[Decimal], initial_balance: Decimal
) -> Metrics:
    """Считает все метрики. Доходность показывается и до, и после комиссий."""
    gross, net, fees = total_pnl(trades)
    base = initial_balance if initial_balance > 0 else Decimal("1")
    average = (net / Decimal(len(trades))) if trades else Decimal("0")
    return Metrics(
        trades_count=len(trades),
        total_return_pct=net / base * HUNDRED,
        total_return_pct_gross=gross / base * HUNDRED,
        net_pnl=net,
        gross_pnl=gross,
        total_fees=fees,
        max_drawdown_pct=max_drawdown_pct(equity_values),
        sharpe=sharpe_ratio(equity_values),
        win_rate_pct=win_rate_pct(trades),
        profit_factor=profit_factor(trades),
        expectancy=expectancy(trades),
        average_trade=average,
    )


def format_report(metrics: Metrics, symbol: str, timeframe: str) -> str:
    """Текстовый отчёт. Разница до и после комиссий видна явно."""
    def money(value: Decimal) -> str:
        return f"{value.quantize(Decimal('0.01'))}"

    lines = [
        f"Бэктест {symbol} {timeframe}",
        f"Сделок: {metrics.trades_count}",
        f"Доходность до комиссий: {money(metrics.total_return_pct_gross)}%"
        f" ({money(metrics.gross_pnl)})",
        f"Доходность после комиссий: {money(metrics.total_return_pct)}%"
        f" ({money(metrics.net_pnl)})",
        f"Комиссии суммарно: {money(metrics.total_fees)}",
        f"Разница до/после комиссий: {money(metrics.gross_pnl - metrics.net_pnl)}",
        f"Максимальная просадка: {money(metrics.max_drawdown_pct)}%",
        f"Sharpe: {money(metrics.sharpe)}",
        f"Win rate: {money(metrics.win_rate_pct)}%",
        f"Profit factor: {money(metrics.profit_factor)}",
        f"Expectancy: {money(metrics.expectancy)}",
        f"Средняя сделка: {money(metrics.average_trade)}",
    ]
    if metrics.net_pnl < 0:
        lines.append("ВНИМАНИЕ: стратегия убыточна на этом периоде. Параметры не подгоняются.")
    return "\n".join(lines)
