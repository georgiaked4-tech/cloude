"""Загрузка исторических свечей в SQLite.

Запуск: python -m scripts.backfill --symbol BTC/USDT --timeframe 1h --pages 5
"""

from __future__ import annotations

import argparse

from src.core.config import load_config
from src.core.db import connect, save_candles
from src.core.log import get_logger, setup_logging
from src.data.market import MarketData

log = get_logger(__name__)


def main() -> None:
    """Скачивает свечи постранично и сохраняет их в базу."""
    parser = argparse.ArgumentParser(description="Backfill OHLCV candles")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--timeframe", default=None)
    parser.add_argument("--pages", type=int, default=1)
    args = parser.parse_args()

    config = load_config()
    setup_logging(config.logging.level, config.logging.json_output)

    symbols = [args.symbol] if args.symbol else config.market.symbols
    timeframe = args.timeframe or config.market.timeframe
    market = MarketData(config.exchange, config.market)
    conn = connect(config.db.path)

    for symbol in symbols:
        since: int | None = None
        for page in range(args.pages):
            candles = market.fetch_ohlcv(symbol, timeframe, since=since)
            if not candles:
                break
            rows = [(c.ts, c.open, c.high, c.low, c.close, c.volume) for c in candles]
            saved = save_candles(conn, symbol, timeframe, rows)
            log.info(
                "candles_saved",
                symbol=symbol,
                timeframe=timeframe,
                page=page + 1,
                count=saved,
            )
            since = candles[-1].ts + 1
    conn.close()


if __name__ == "__main__":
    main()
