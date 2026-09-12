"""Движок бэктеста.

Использует ту же стратегию, тот же риск-модуль и того же брокера, что и paper-режим.
Дублирования торговой логики нет.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.backtest.metrics import Metrics, compute_metrics
from src.core.config import AppConfig
from src.paper.broker import EXIT_FORCED, EXIT_SIGNAL, PaperBroker, Trade
from src.risk.limits import RiskManager
from src.strategy.base import SIDE_BUY, SIDE_SELL, BaseStrategy, Candle


@dataclass
class BacktestResult:
    """Результат прогона: сделки, кривая капитала и метрики."""

    symbol: str
    timeframe: str
    trades: list[Trade]
    equity_values: list[Decimal]
    metrics: Metrics


def run_backtest(
    candles: list[Candle],
    strategy: BaseStrategy,
    config: AppConfig,
    symbol: str,
    timeframe: str,
) -> BacktestResult:
    """Прогоняет стратегию по историческим свечам.

    Порядок обработки каждой свечи:
    1) проверка стопа и тейка по открытой позиции;
    2) обновление стратегии и получение сигнала;
    3) вход или выход с учётом лимитов риска;
    4) запись точки кривой капитала.
    """
    risk = RiskManager(config.risk)
    broker = PaperBroker(balance=config.risk.initial_balance, costs=config.costs, risk=risk)
    equity_values: list[Decimal] = []

    for candle in candles:
        prices = {symbol: candle.close}
        broker.on_candle(symbol, candle)

        signal = strategy.update(candle)
        if signal is not None:
            if signal.side == SIDE_BUY:
                broker.try_open(signal)
            elif signal.side == SIDE_SELL:
                broker.close(symbol, candle.ts, candle.close, EXIT_SIGNAL)

        broker.record_equity(candle.ts, prices)
        equity_values.append(broker.equity(prices))

    if candles:
        last = candles[-1]
        broker.close_all(last.ts, {symbol: last.close}, EXIT_FORCED)
        equity_values.append(broker.equity({symbol: last.close}))

    metrics = compute_metrics(broker.trades, equity_values, config.risk.initial_balance)
    return BacktestResult(
        symbol=symbol,
        timeframe=timeframe,
        trades=broker.trades,
        equity_values=equity_values,
        metrics=metrics,
    )
