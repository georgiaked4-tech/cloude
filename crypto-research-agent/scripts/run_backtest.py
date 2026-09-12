"""Прогон бэктеста по сохранённым свечам.

Запуск: python -m scripts.run_backtest --symbol BTC/USDT --timeframe 1h
"""

from __future__ import annotations

import argparse

from src.backtest.engine import run_backtest
from src.backtest.metrics import format_report
from src.core.config import load_config
from src.core.db import connect, load_candles
from src.core.log import setup_logging
from src.strategy.base import Candle
from src.strategy.ema_cross import build_strategy


def main() -> None:
    """Читает свечи из базы, прогоняет стратегию и печатает отчёт."""
    parser = argparse.ArgumentParser(description="Run backtest")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--timeframe", default=None)
    args = parser.parse_args()

    config = load_config()
    setup_logging(config.logging.level, config.logging.json_output)

    symbol = args.symbol or config.market.symbols[0]
    timeframe = args.timeframe or config.market.timeframe

    conn = connect(config.db.path)
    rows = load_candles(conn, symbol, timeframe)
    conn.close()

    if not rows:
        print(f"Нет свечей для {symbol} {timeframe}. Сначала запустите scripts/backfill.py")
        return

    candles = [Candle.from_row(row) for row in rows]
    strategy = build_strategy(symbol, config.strategy.params)
    result = run_backtest(candles, strategy, config, symbol, timeframe)
    print(format_report(result.metrics, symbol, timeframe))


if __name__ == "__main__":
    main()
