"""Метрики бэктеста, рассчитанные без float."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal

from src.core.timeframe import periods_per_year
from src.paper.broker import PaperTrade


@dataclass(frozen=True)
class BacktestMetrics:
    total_return_before_fees_pct: Decimal
    total_return_after_fees_pct: Decimal
    max_drawdown_pct: Decimal
    sharpe: Decimal
    win_rate_pct: Decimal
    profit_factor: Decimal | None
    expectancy: Decimal
    average_trade: Decimal
    trades: int
    total_fees: Decimal

    def as_dict(self) -> dict[str, str | int | None]:
        """Подготовить JSON-совместимый отчёт без потери точности Decimal."""

        return {
            key: str(value) if isinstance(value, Decimal) else value
            for key, value in asdict(self).items()
        }


def _max_drawdown(equity: list[Decimal]) -> Decimal:
    if not equity:
        return Decimal(0)
    peak = equity[0]
    worst = Decimal(0)
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            worst = max(worst, (peak - value) / peak * Decimal(100))
    return worst


def _sharpe(equity: list[Decimal], annualization: Decimal) -> Decimal:
    """Sharpe = средняя доходность бара / стандартное отклонение × √(баров в году)."""

    if len(equity) < 3:
        return Decimal(0)
    returns = [equity[index] / equity[index - 1] - 1 for index in range(1, len(equity))]
    mean = sum(returns, Decimal(0)) / Decimal(len(returns))
    variance = sum((item - mean) ** 2 for item in returns) / Decimal(len(returns) - 1)
    if variance == 0:
        return Decimal(0)
    return mean / variance.sqrt() * annualization.sqrt()


def calculate_metrics(
    trades: list[PaperTrade],
    equity: list[Decimal],
    initial_balance: Decimal,
    timeframe: str = "1d",
) -> BacktestMetrics:
    """Посчитать обязательные метрики с отдельным результатом до/после комиссий."""

    total_fees = sum((trade.fee for trade in trades), Decimal(0))
    net_pnl = sum((trade.pnl for trade in trades), Decimal(0))
    gross_pnl = net_pnl + total_fees
    wins = [trade.pnl for trade in trades if trade.pnl > 0]
    losses = [trade.pnl for trade in trades if trade.pnl < 0]
    trade_count = len(trades)
    gross_profit = sum(wins, Decimal(0))
    gross_loss = abs(sum(losses, Decimal(0)))
    average = net_pnl / Decimal(trade_count) if trade_count else Decimal(0)
    win_rate = Decimal(len(wins)) / Decimal(trade_count) * 100 if trade_count else Decimal(0)
    # Ожидание = доля прибыльных × средний профит − доля убыточных × средний убыток.
    # Алгебраически это то же число, что average_trade; считаем явно, чтобы в
    # отчёте было видно, из каких долей оно складывается.
    if trade_count:
        average_win = gross_profit / Decimal(len(wins)) if wins else Decimal(0)
        average_loss = gross_loss / Decimal(len(losses)) if losses else Decimal(0)
        win_share = Decimal(len(wins)) / Decimal(trade_count)
        loss_share = Decimal(len(losses)) / Decimal(trade_count)
        expectancy = win_share * average_win - loss_share * average_loss
    else:
        expectancy = Decimal(0)

    return BacktestMetrics(
        total_return_before_fees_pct=gross_pnl / initial_balance * 100,
        total_return_after_fees_pct=net_pnl / initial_balance * 100,
        max_drawdown_pct=_max_drawdown(equity),
        sharpe=_sharpe(equity, periods_per_year(timeframe)),
        win_rate_pct=win_rate,
        profit_factor=gross_profit / gross_loss if gross_loss else None,
        expectancy=expectancy,
        average_trade=average,
        trades=trade_count,
        total_fees=total_fees,
    )

