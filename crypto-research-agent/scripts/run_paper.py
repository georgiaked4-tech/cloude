"""Paper-режим: свежие свечи с биржи, те же стратегия, риск-модуль и брокер, что в бэктесте.

Реальные ордера не отправляются. Запуск: python -m scripts.run_paper --once
"""

from __future__ import annotations

import argparse
import time

from src.core.config import load_config
from src.core.db import connect, save_equity, save_signal, save_trade, set_signal_status
from src.core.log import get_logger, setup_logging
from src.data.market import MarketData
from src.paper.broker import EXIT_SIGNAL, PaperBroker
from src.risk.limits import RiskManager
from src.strategy.base import SIDE_BUY, SIDE_SELL
from src.strategy.ema_cross import build_strategy

log = get_logger(__name__)


def main() -> None:
    """Один проход или бесконечный цикл опроса рынка."""
    parser = argparse.ArgumentParser(description="Run paper trading loop")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-sec", type=int, default=60)
    args = parser.parse_args()

    config = load_config()
    setup_logging(config.logging.level, config.logging.json_output)

    symbol = args.symbol or config.market.symbols[0]
    timeframe = config.market.timeframe

    market = MarketData(config.exchange, config.market)
    conn = connect(config.db.path)
    risk = RiskManager(config.risk)
    broker = PaperBroker(balance=config.risk.initial_balance, costs=config.costs, risk=risk)
    strategy = build_strategy(symbol, config.strategy.params)

    seen_ts: int | None = None
    while True:
        candles = market.fetch_ohlcv(symbol, timeframe, limit=max(strategy.warmup * 3, 100))
        # Последняя свеча может быть незакрытой, поэтому берём предпоследнюю.
        closed = candles[:-1]
        for candle in closed:
            if seen_ts is not None and candle.ts <= seen_ts:
                continue
            seen_ts = candle.ts

            closed_trade = broker.on_candle(symbol, candle)
            if closed_trade is not None:
                save_trade(conn, closed_trade.as_row())

            signal = strategy.update(candle)
            if signal is not None:
                signal_id = save_signal(
                    conn,
                    signal.ts,
                    symbol,
                    strategy.name,
                    signal.side,
                    signal.price,
                    signal.reason,
                    "new",
                )
                if signal.side == SIDE_BUY:
                    position = broker.try_open(signal, signal_id=signal_id)
                    set_signal_status(conn, signal_id, "opened" if position else "skipped")
                elif signal.side == SIDE_SELL:
                    trade = broker.close(symbol, candle.ts, candle.close, EXIT_SIGNAL)
                    if trade is not None:
                        save_trade(conn, trade.as_row())
                    set_signal_status(conn, signal_id, "opened" if trade else "skipped")

            prices = {symbol: candle.close}
            save_equity(conn, candle.ts, broker.balance, broker.open_value(prices))

        log.info(
            "paper_tick",
            symbol=symbol,
            balance=str(broker.balance),
            positions=broker.open_positions,
        )
        if args.once:
            break
        time.sleep(args.interval_sec)

    conn.close()


if __name__ == "__main__":
    main()
