"""Однопроходный paper-запуск по последним закрытым публичным свечам."""

from __future__ import annotations

import argparse
import json
import time
from decimal import Decimal

from src.core.config import AppConfig, load_config
from src.core.db import Database, PaperState
from src.core.log import configure_logging, get_logger
from src.core.timeframe import is_closed, timeframe_ms
from src.data.market import MarketDataClient
from src.paper.broker import PaperBroker
from src.risk.limits import RiskManager, utc_day_start_ms
from src.strategy.base import Candle
from src.strategy.ema_cross import EmaCrossStrategy

Row = tuple[int, Decimal, Decimal, Decimal, Decimal, Decimal]
PAGE_LIMIT = 1000
MAX_PAGES = 20


def fetch_rows(
    client: MarketDataClient,
    symbol: str,
    timeframe: str,
    since_ts: int | None,
    warmup_limit: int,
    now_ms: int,
) -> list[Row]:
    """Загрузить свечи начиная с чекпоинта, при необходимости постранично.

    Один запрос отдаёт окно фиксированного размера. Если планировщик молчал
    дольше этого окна, часть интервала после чекпоинта потерялась бы вместе с
    произошедшими в ней срабатываниями стопа, поэтому загрузка идёт страницами
    от `since_ts` и до текущего момента.
    """

    if since_ts is None:
        return client.fetch_ohlcv(symbol, timeframe, limit=warmup_limit)

    duration = timeframe_ms(timeframe)
    collected: dict[int, Row] = {}
    cursor = since_ts + 1
    for _ in range(MAX_PAGES):
        page = [row for row in client.fetch_ohlcv(
            symbol, timeframe, limit=PAGE_LIMIT, since=cursor
        ) if row[0] >= cursor]
        if not page:
            break
        collected.update({row[0]: row for row in page})
        last_ts = page[-1][0]
        if last_ts + duration > now_ms:
            break
        cursor = last_ts + 1
    return [collected[ts] for ts in sorted(collected)]


def merge_candles(
    stored: list[Row], fetched: list[Row], timeframe: str, now_ms: int
) -> list[Candle]:
    """Объединить историю из базы со свежими свечами, отбросив незакрытые.

    Стратегия прогревается по всей сохранённой истории, а не по одному окну:
    EMA рекурсивна и не имеет точного конечного прогрева, поэтому короткое окно
    давало бы состояние, отличное от бэктеста на тех же данных.
    """

    merged: dict[int, Row] = {row[0]: row for row in stored}
    merged.update({row[0]: row for row in fetched})
    return [
        Candle(*merged[ts]) for ts in sorted(merged) if is_closed(ts, timeframe, now_ms)
    ]


def initial_state(
    config: AppConfig, symbol: str, timeframe: str, candles: list[Candle]
) -> PaperState:
    """Чекпоинт первого запуска: торгуем с текущей свечи, историю не отыгрываем."""

    # Свечи старше предпоследней нужны только для прогрева индикатора, иначе
    # первый же запуск отыграл бы всю загруженную историю задним числом.
    last_ts = candles[-2].ts if len(candles) >= 2 else candles[-1].ts - 1
    return PaperState(
        symbol=symbol,
        timeframe=timeframe,
        last_ts=last_ts,
        balance=config.trading.initial_balance,
        day_start_ts=utc_day_start_ms(candles[-1].ts),
        day_start_equity=config.trading.initial_balance,
    )


def main() -> None:
    config = load_config()
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default=config.trading.symbols[0])
    parser.add_argument("--timeframe", default=config.trading.timeframe)
    parser.add_argument("--once", action="store_true", help="Совместимость с планировщиком")
    parser.add_argument("--limit", type=int, help="Сколько свечей запросить для прогрева")
    args = parser.parse_args()

    symbol, timeframe = args.symbol, args.timeframe
    configure_logging(config.logging.level)
    logger = get_logger()
    database = Database(config.project_root / config.storage.database_path)
    database.initialize()

    state = database.load_paper_state(symbol, timeframe)
    now_ms = int(time.time() * 1000)
    fetched = fetch_rows(
        MarketDataClient(config.exchange),
        symbol,
        timeframe,
        state.last_ts if state is not None else None,
        args.limit or config.strategy.slow_ema + 50,
        now_ms,
    )
    if fetched:
        database.upsert_candles(
            symbol, timeframe,
            [row for row in fetched if is_closed(row[0], timeframe, now_ms)],
        )
    candles = merge_candles(
        database.load_candles(symbol, timeframe), fetched, timeframe, now_ms
    )
    if not candles:
        print(json.dumps({"mode": "paper", "real_orders": False,
                          "error": "Нет закрытых свечей"}, ensure_ascii=False, indent=2))
        return

    if state is None:
        state = initial_state(config, symbol, timeframe, candles)
    broker = PaperBroker(config.trading, RiskManager(config.risk))
    open_trade_ids: dict[str, int] = {}
    for trade in database.load_open_paper_trades(symbol):
        broker.restore_position(
            trade.signal_id, trade.symbol, trade.qty, trade.entry_price,
            trade.entry_ts, trade.entry_fee,
        )
        open_trade_ids[trade.symbol] = trade.trade_id
    broker.set_state(
        state.balance,
        state.day_start_equity,
        database.realized_pnl_since(state.day_start_ts, symbol),
    )
    strategy = EmaCrossStrategy(config.strategy.fast_ema, config.strategy.slow_ema)

    processed = 0
    last_signal = None
    last_action = "Новых закрытых свечей нет"
    day_start_ts, day_start_equity = state.day_start_ts, state.day_start_equity
    for candle in candles:
        if candle.ts <= state.last_ts:
            strategy.on_candle(symbol, candle)  # только прогрев индикатора
            continue

        candle_day = utc_day_start_ms(candle.ts)
        if candle_day != day_start_ts:
            day_start_ts = candle_day
            day_start_equity = broker.equity({symbol: candle.open})
            broker.reset_utc_day(day_start_equity)

        stopped = broker.process_price(
            symbol, candle.open, candle.low, candle.high, candle.ts
        )
        if stopped is not None:
            last_action = f"Позиция закрыта: {stopped.exit_reason}"
        signal = strategy.on_candle(symbol, candle)
        exited = None
        opened = False
        if signal is not None:
            last_signal = signal
            if signal.side == "buy":
                opened, reason = broker.open_long(0, signal)
                last_action = reason
            elif symbol in broker.positions:
                exited = broker.close_long(symbol, signal.price, signal.ts, "strategy_exit")
                last_action = "Позиция закрыта: strategy_exit"

        processed += 1
        open_value = broker.equity({symbol: candle.close}) - broker.balance
        # Сделка, баланс и чекпоинт пишутся одной транзакцией: иначе падение
        # между ними оставило бы позицию с балансом, не учитывающим вход.
        with database.session() as connection:
            for trade in (stopped, exited):
                if trade is not None:
                    database.close_paper_trade(
                        open_trade_ids.pop(symbol), trade.exit_price, trade.exit_ts,
                        trade.fee, trade.pnl, trade.pnl_pct, trade.exit_reason,
                        connection=connection,
                    )
            if signal is not None:
                signal_id = database.insert_signal(
                    signal.ts, signal.symbol, signal.strategy, signal.side,
                    signal.price, signal.reason,
                    status="opened" if opened else "skipped",
                    connection=connection,
                )
                if opened:
                    position = broker.positions[symbol]
                    position.signal_id = signal_id
                    open_trade_ids[symbol] = database.open_paper_trade(
                        signal_id, symbol, "long", position.qty, position.entry_price,
                        position.entry_ts, position.entry_fee, connection=connection,
                    )
            database.record_equity(
                candle.ts, broker.balance, open_value, connection=connection
            )
            database.save_paper_state(
                PaperState(symbol, timeframe, candle.ts, broker.balance,
                           day_start_ts, day_start_equity),
                connection=connection,
            )

    position = broker.positions.get(symbol)
    result = {
        "mode": "paper",
        "real_orders": False,
        "symbol": symbol,
        "timeframe": timeframe,
        "closed_candles_processed": processed,
        "last_candle_ts": candles[-1].ts,
        "last_signal": last_signal.side if last_signal else None,
        "reason": last_signal.reason if last_signal else "Нового пересечения EMA нет",
        "action": last_action,
        "balance": str(broker.balance),
        "equity": str(broker.equity({symbol: candles[-1].close})),
        "open_position": None if position is None else {
            "qty": str(position.qty),
            "entry_price": str(position.entry_price),
            "stop_price": str(position.stop_price),
            "take_price": str(position.take_price),
        },
    }
    logger.info("paper_run_complete", symbol=symbol, processed=processed)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
