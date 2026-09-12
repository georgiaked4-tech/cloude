"""Загрузить публичные исторические свечи в SQLite."""

from __future__ import annotations

import argparse
import time

from src.core.config import load_config
from src.core.db import Database
from src.core.log import configure_logging, get_logger
from src.core.timeframe import is_closed
from src.data.market import MarketDataClient


def main() -> None:
    config = load_config()
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default=config.trading.symbols[0])
    parser.add_argument("--timeframe", default=config.trading.timeframe)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--since", type=int)
    args = parser.parse_args()

    configure_logging(config.logging.level)
    database = Database(config.project_root / config.storage.database_path)
    database.initialize()
    candles = MarketDataClient(config.exchange).fetch_ohlcv(
        args.symbol, args.timeframe, args.limit, args.since
    )
    # Последняя свеча ещё формируется: её high/low/close изменятся, а бэктест
    # обязан быть воспроизводимым, поэтому в базу она не попадает.
    now_ms = int(time.time() * 1000)
    closed = [row for row in candles if is_closed(row[0], args.timeframe, now_ms)]
    count = database.upsert_candles(args.symbol, args.timeframe, closed)
    get_logger().info(
        "backfill_complete", symbol=args.symbol, candles=count,
        skipped_forming=len(candles) - count,
    )


if __name__ == "__main__":
    main()

