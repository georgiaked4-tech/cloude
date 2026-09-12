"""Однопроходный paper-запуск по последним закрытым публичным свечам."""

from __future__ import annotations

import argparse
import json
import time
from decimal import Decimal

from src.core.config import AppConfig, load_config
from src.core.db import Database
from src.core.log import configure_logging, get_logger
from src.core.timeframe import is_closed
from src.data.market import MarketDataClient
from src.paper.broker import PaperBroker, PaperTrade
from src.risk.limits import RiskManager, utc_day_start_ms
from src.strategy.base import Candle
from src.strategy.ema_cross import EmaCrossStrategy


def closed_candles(
    rows: list[tuple[int, Decimal, Decimal, Decimal, Decimal, Decimal]],
    timeframe: str,
    now_ms: int,
) -> list[Candle]:
    """Отбросить свечи, которые ещё формируются."""

    return [Candle(*row) for row in rows if is_closed(row[0], timeframe, now_ms)]


def restore_broker(
    database: Database, config: AppConfig, symbol: str, day_start_ts: int
) -> tuple[PaperBroker, dict[str, int]]:
    """Восстановить баланс, открытые позиции и дневные счётчики из БД.

    Скрипт рассчитан на запуск по расписанию (`--once`), поэтому состояние между
    запусками живёт только в базе: без восстановления каждый запуск начинал бы с
    начального депозита и заново открывал позицию.
    """

    broker = PaperBroker(config.trading, RiskManager(config.risk))
    snapshot = database.latest_equity()
    balance = snapshot[1] if snapshot is not None else config.trading.initial_balance
    open_trade_ids: dict[str, int] = {}
    for trade in database.load_open_paper_trades(symbol):
        broker.restore_position(
            trade.signal_id, trade.symbol, trade.qty, trade.entry_price,
            trade.entry_ts, trade.entry_fee,
        )
        open_trade_ids[trade.symbol] = trade.trade_id
    day_start_balance = database.equity_at_day_start(day_start_ts) or balance
    daily_pnl = database.realized_pnl_since(day_start_ts)
    broker.set_state(balance, day_start_balance, daily_pnl)
    return broker, open_trade_ids


def persist_close(database: Database, trade_id: int, trade: PaperTrade) -> None:
    """Дописать закрытие сделки в уже созданную строку paper_trades."""

    database.close_paper_trade(
        trade_id, trade.exit_price, trade.exit_ts, trade.fee,
        trade.pnl, trade.pnl_pct, trade.exit_reason,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--once", action="store_true", help="Совместимость с планировщиком")
    parser.add_argument("--limit", type=int, help="Сколько свечей запросить для прогрева")
    args = parser.parse_args()

    config = load_config()
    configure_logging(config.logging.level)
    logger = get_logger()
    database = Database(config.project_root / config.storage.database_path)
    database.initialize()

    limit = args.limit or config.strategy.slow_ema + 50
    rows = MarketDataClient(config.exchange).fetch_ohlcv(
        args.symbol, args.timeframe, limit=limit
    )
    candles = closed_candles(rows, args.timeframe, int(time.time() * 1000))
    if not candles:
        print(json.dumps({"mode": "paper", "real_orders": False,
                          "error": "Нет закрытых свечей"}, ensure_ascii=False, indent=2))
        return
    database.upsert_candles(
        args.symbol, args.timeframe, [tuple(row) for row in rows[: len(candles)]]
    )

    snapshot = database.latest_equity()
    last_processed_ts = snapshot[0] if snapshot is not None else 0
    current_day = utc_day_start_ms(candles[-1].ts)
    broker, open_trade_ids = restore_broker(database, config, args.symbol, current_day)
    strategy = EmaCrossStrategy(config.strategy.fast_ema, config.strategy.slow_ema)

    processed = 0
    last_signal = None
    last_action = "Новых закрытых свечей нет"
    for candle in candles:
        # Свечи старше последнего сохранённого среза нужны только для прогрева EMA.
        fresh = candle.ts > last_processed_ts
        if fresh:
            candle_day = utc_day_start_ms(candle.ts)
            if candle_day != current_day:
                broker.reset_utc_day(broker.equity({args.symbol: candle.open}))
                current_day = candle_day
            closed = broker.process_price(args.symbol, candle.low, candle.high, candle.ts)
            if closed is not None:
                persist_close(database, open_trade_ids.pop(args.symbol), closed)
                last_action = f"Позиция закрыта: {closed.exit_reason}"

        signal = strategy.on_candle(args.symbol, candle)
        if not fresh:
            continue

        processed += 1
        if signal is not None:
            last_signal = signal
            signal_id = database.insert_signal(
                signal.ts, signal.symbol, signal.strategy, signal.side,
                signal.price, signal.reason,
            )
            if signal.side == "buy":
                opened, reason = broker.open_long(signal_id, signal)
                database.set_signal_status(signal_id, "opened" if opened else "skipped")
                last_action = reason
                if opened:
                    position = broker.positions[args.symbol]
                    open_trade_ids[args.symbol] = database.open_paper_trade(
                        signal_id, args.symbol, "long", position.qty,
                        position.entry_price, position.entry_ts, position.entry_fee,
                    )
            else:
                database.set_signal_status(signal_id, "skipped")
                if args.symbol in broker.positions:
                    closed = broker.close_long(
                        args.symbol, signal.price, signal.ts, "strategy_exit"
                    )
                    persist_close(database, open_trade_ids.pop(args.symbol), closed)
                    last_action = "Позиция закрыта: strategy_exit"

        open_value = broker.equity({args.symbol: candle.close}) - broker.balance
        database.record_equity(candle.ts, broker.balance, open_value)

    position = broker.positions.get(args.symbol)
    result = {
        "mode": "paper",
        "real_orders": False,
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "closed_candles_processed": processed,
        "last_candle_ts": candles[-1].ts,
        "last_signal": last_signal.side if last_signal else None,
        "reason": last_signal.reason if last_signal else "Нового пересечения EMA нет",
        "action": last_action,
        "balance": str(broker.balance),
        "equity": str(broker.equity({args.symbol: candles[-1].close})),
        "open_position": None if position is None else {
            "qty": str(position.qty),
            "entry_price": str(position.entry_price),
            "stop_price": str(position.stop_price),
            "take_price": str(position.take_price),
        },
    }
    logger.info("paper_run_complete", symbol=args.symbol, processed=processed)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
