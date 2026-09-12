"""Запустить воспроизводимый бэктест по свечам из SQLite."""

from __future__ import annotations

import argparse
import json

from src.backtest.engine import BacktestEngine
from src.core.config import load_config
from src.core.db import Database
from src.paper.broker import PaperBroker
from src.risk.limits import RiskManager
from src.strategy.base import Candle
from src.strategy.ema_cross import EmaCrossStrategy


def main() -> None:
    config = load_config()
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default=config.trading.symbols[0])
    parser.add_argument("--timeframe", default=config.trading.timeframe)
    args = parser.parse_args()

    database = Database(config.project_root / config.storage.database_path)
    database.initialize()
    rows = database.load_candles(args.symbol, args.timeframe)
    if not rows:
        raise SystemExit(
            f"Нет свечей {args.symbol} {args.timeframe}. Сначала запустите scripts/backfill.py"
        )
    candles = [Candle(*row) for row in rows]
    strategy = EmaCrossStrategy(config.strategy.fast_ema, config.strategy.slow_ema)
    broker = PaperBroker(config.trading, RiskManager(config.risk))
    report = BacktestEngine(strategy, broker).run(args.symbol, candles, args.timeframe)
    print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

