"""Бэктест на том же коде стратегии и broker, что используется в paper-режиме."""

from __future__ import annotations

from decimal import Decimal

from src.backtest.metrics import BacktestMetrics, calculate_metrics
from src.paper.broker import PaperBroker
from src.risk.limits import utc_day_start_ms
from src.strategy.base import BaseStrategy, Candle


class BacktestEngine:
    """Последовательно проигрывает закрытые свечи без заглядывания вперёд."""

    def __init__(self, strategy: BaseStrategy, broker: PaperBroker) -> None:
        self.strategy = strategy
        self.broker = broker

    def run(
        self, symbol: str, candles: list[Candle], timeframe: str | None = None
    ) -> BacktestMetrics:
        """Выполнить бэктест и вернуть метрики после принудительного закрытия в конце."""

        if not candles:
            raise ValueError("Для бэктеста нужны свечи")
        timeframe = timeframe or self.broker.trading.timeframe
        initial_balance = self.broker.trading.initial_balance
        equity: list[Decimal] = [initial_balance]
        current_day = utc_day_start_ms(candles[0].ts)
        signal_id = 0

        for candle in candles:
            candle_day = utc_day_start_ms(candle.ts)
            if candle_day != current_day:
                # База дневного лимита — капитал на начало дня вместе с позициями.
                self.broker.reset_utc_day(self.broker.equity({symbol: candle.open}))
                current_day = candle_day

            self.broker.process_price(symbol, candle.low, candle.high, candle.ts)
            signal = self.strategy.on_candle(symbol, candle)
            if signal is not None:
                signal_id += 1
                if signal.side == "buy":
                    self.broker.open_long(signal_id, signal)
                elif symbol in self.broker.positions:
                    self.broker.close_long(symbol, signal.price, signal.ts, "strategy_exit")

            equity.append(self.broker.equity({symbol: candle.close}))

        if symbol in self.broker.positions:
            last = candles[-1]
            self.broker.close_long(symbol, last.close, last.ts, "end_of_backtest")
            equity.append(self.broker.balance)

        return calculate_metrics(
            self.broker.closed_trades, equity, initial_balance, timeframe
        )
