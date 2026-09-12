"""Загрузить публичные исторические свечи в SQLite."""

from __future__ import annotations

import argparse

from src.core.config import load_config
from src.core.db import Database
from src.core.log import configure_logging, get_logger
from src.data.market import MarketDataClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--since", type=int)
    args = parser.parse_args()

    config = load_config()
    configure_logging(config.logging.level)
    database = Database(config.project_root / config.storage.database_path)
    database.initialize()
    candles = MarketDataClient(config.exchange).fetch_ohlcv(
        args.symbol, args.timeframe, args.limit, args.since
    )
    count = database.upsert_candles(args.symbol, args.timeframe, candles)
    get_logger().info("backfill_complete", symbol=args.symbol, candles=count)


if __name__ == "__main__":
    main()

