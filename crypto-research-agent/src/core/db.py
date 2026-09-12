"""SQLite-хранилище проекта."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS candles(
    symbol TEXT, timeframe TEXT, ts INTEGER, open TEXT, high TEXT,
    low TEXT, close TEXT, volume TEXT, PRIMARY KEY(symbol, timeframe, ts)
);
CREATE TABLE IF NOT EXISTS signals(
    id INTEGER PRIMARY KEY, ts INTEGER, symbol TEXT, strategy TEXT, side TEXT,
    price TEXT, reason TEXT, status TEXT CHECK(status IN ('new','opened','skipped'))
);
CREATE TABLE IF NOT EXISTS paper_trades(
    id INTEGER PRIMARY KEY, signal_id INTEGER, symbol TEXT, side TEXT,
    qty TEXT, entry_price TEXT, entry_ts INTEGER, exit_price TEXT,
    exit_ts INTEGER, fee TEXT, pnl TEXT, pnl_pct TEXT, exit_reason TEXT
);
CREATE TABLE IF NOT EXISTS equity(ts INTEGER PRIMARY KEY, balance TEXT, open_value TEXT);
CREATE TABLE IF NOT EXISTS news_items(
    id INTEGER PRIMARY KEY, ts INTEGER, source TEXT, url TEXT UNIQUE,
    title TEXT, summary TEXT, relevance INTEGER
);
CREATE TABLE IF NOT EXISTS digests(date TEXT PRIMARY KEY, content TEXT, sent_ts INTEGER);
-- Состояние paper-режима хранится отдельно для каждой пары символ+таймфрейм:
-- общий срез equity не годится как чекпоинт, потому что два запуска по разным
-- символам в одной базе перетирали бы отметку друг друга.
CREATE TABLE IF NOT EXISTS paper_state(
    symbol TEXT, timeframe TEXT, last_ts INTEGER, balance TEXT,
    day_start_ts INTEGER, day_start_equity TEXT,
    PRIMARY KEY(symbol, timeframe)
);
"""


@dataclass(frozen=True)
class PaperState:
    """Чекпоинт paper-режима по одной паре символ+таймфрейм."""

    symbol: str
    timeframe: str
    last_ts: int
    balance: Decimal
    day_start_ts: int
    day_start_equity: Decimal


@dataclass(frozen=True)
class OpenPaperTrade:
    """Строка paper_trades без даты выхода, то есть незакрытая позиция."""

    trade_id: int
    signal_id: int
    symbol: str
    qty: Decimal
    entry_price: Decimal
    entry_ts: int
    entry_fee: Decimal


class Database:
    """Минимальная обёртка SQLite без скрытой ORM-логики."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        """Открыть соединение с именованным доступом к колонкам."""

        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        """Соединение с коммитом транзакции и гарантированным закрытием.

        `with connection:` в sqlite3 только фиксирует транзакцию, но не закрывает
        соединение, поэтому закрытие вынесено в `finally`.
        """

        connection = self.connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @contextmanager
    def _use(self, connection: sqlite3.Connection | None) -> Iterator[sqlite3.Connection]:
        """Писать в переданное соединение либо открыть собственную транзакцию.

        Благодаря этому несколько записей (сделка, сигнал, чекпоинт) можно
        выполнить одной транзакцией: иначе падение между ними оставило бы
        открытую позицию с балансом, не учитывающим вход.
        """

        if connection is not None:
            yield connection
        else:
            with self.session() as owned:
                yield owned

    def initialize(self) -> None:
        """Создать таблицы, если их ещё нет."""

        with self.session() as connection:
            connection.executescript(SCHEMA)

    def upsert_candles(
        self,
        symbol: str,
        timeframe: str,
        rows: Iterable[tuple[int, Decimal, Decimal, Decimal, Decimal, Decimal]],
    ) -> int:
        """Сохранить свечи, сериализовав Decimal как строки."""

        values = [
            (symbol, timeframe, ts, *(str(value) for value in candle))
            for ts, *candle in rows
        ]
        with self.session() as connection:
            connection.executemany(
                """INSERT OR REPLACE INTO candles
                (symbol,timeframe,ts,open,high,low,close,volume)
                VALUES (?,?,?,?,?,?,?,?)""",
                values,
            )
        return len(values)

    def load_candles(
        self, symbol: str, timeframe: str
    ) -> list[tuple[int, Decimal, Decimal, Decimal, Decimal, Decimal]]:
        """Загрузить свечи в хронологическом порядке."""

        with self.session() as connection:
            rows = connection.execute(
                """SELECT ts,open,high,low,close,volume FROM candles
                WHERE symbol=? AND timeframe=? ORDER BY ts""",
                (symbol, timeframe),
            ).fetchall()
        return [
            (
                row["ts"],
                *(Decimal(row[name]) for name in ("open", "high", "low", "close", "volume")),
            )
            for row in rows
        ]

    def insert_signal(
        self,
        ts: int,
        symbol: str,
        strategy: str,
        side: str,
        price: Decimal,
        reason: str,
        status: str = "new",
        connection: sqlite3.Connection | None = None,
    ) -> int:
        """Записать сигнал стратегии и вернуть его идентификатор."""

        with self._use(connection) as active:
            cursor = active.execute(
                """INSERT INTO signals (ts,symbol,strategy,side,price,reason,status)
                VALUES (?,?,?,?,?,?,?)""",
                (ts, symbol, strategy, side, str(price), reason, status),
            )
        return int(cursor.lastrowid or 0)

    def set_signal_status(
        self, signal_id: int, status: str, connection: sqlite3.Connection | None = None
    ) -> None:
        """Обновить статус сигнала: new | opened | skipped."""

        with self._use(connection) as active:
            active.execute("UPDATE signals SET status=? WHERE id=?", (status, signal_id))

    def open_paper_trade(
        self,
        signal_id: int,
        symbol: str,
        side: str,
        qty: Decimal,
        entry_price: Decimal,
        entry_ts: int,
        entry_fee: Decimal,
        connection: sqlite3.Connection | None = None,
    ) -> int:
        """Создать строку сделки без цены выхода — это открытая позиция."""

        with self._use(connection) as active:
            cursor = active.execute(
                """INSERT INTO paper_trades
                (signal_id,symbol,side,qty,entry_price,entry_ts,fee)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    signal_id, symbol, side, str(qty), str(entry_price),
                    entry_ts, str(entry_fee),
                ),
            )
        return int(cursor.lastrowid or 0)

    def close_paper_trade(
        self,
        trade_id: int,
        exit_price: Decimal,
        exit_ts: int,
        fee: Decimal,
        pnl: Decimal,
        pnl_pct: Decimal,
        exit_reason: str,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        """Дописать в открытую сделку цену выхода, суммарную комиссию и PnL."""

        with self._use(connection) as active:
            active.execute(
                """UPDATE paper_trades
                SET exit_price=?, exit_ts=?, fee=?, pnl=?, pnl_pct=?, exit_reason=?
                WHERE id=?""",
                (
                    str(exit_price), exit_ts, str(fee), str(pnl),
                    str(pnl_pct), exit_reason, trade_id,
                ),
            )

    def load_open_paper_trades(self, symbol: str) -> list[OpenPaperTrade]:
        """Вернуть незакрытые позиции по символу для восстановления состояния."""

        with self.session() as connection:
            rows = connection.execute(
                """SELECT id,signal_id,symbol,qty,entry_price,entry_ts,fee
                FROM paper_trades WHERE symbol=? AND exit_ts IS NULL ORDER BY entry_ts""",
                (symbol,),
            ).fetchall()
        return [
            OpenPaperTrade(
                trade_id=row["id"],
                signal_id=row["signal_id"],
                symbol=row["symbol"],
                qty=Decimal(row["qty"]),
                entry_price=Decimal(row["entry_price"]),
                entry_ts=row["entry_ts"],
                entry_fee=Decimal(row["fee"]),
            )
            for row in rows
        ]

    def record_equity(
        self,
        ts: int,
        balance: Decimal,
        open_value: Decimal,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        """Сохранить срез капитала: свободный баланс и оценку открытых позиций."""

        with self._use(connection) as active:
            active.execute(
                "INSERT OR REPLACE INTO equity (ts,balance,open_value) VALUES (?,?,?)",
                (ts, str(balance), str(open_value)),
            )

    def latest_equity(self) -> tuple[int, Decimal, Decimal] | None:
        """Последний сохранённый срез капитала или None, если истории нет."""

        with self.session() as connection:
            row = connection.execute(
                "SELECT ts,balance,open_value FROM equity ORDER BY ts DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return row["ts"], Decimal(row["balance"]), Decimal(row["open_value"])

    def load_paper_state(self, symbol: str, timeframe: str) -> PaperState | None:
        """Чекпоинт paper-режима по паре символ+таймфрейм или None при первом запуске."""

        with self.session() as connection:
            row = connection.execute(
                """SELECT symbol,timeframe,last_ts,balance,day_start_ts,day_start_equity
                FROM paper_state WHERE symbol=? AND timeframe=?""",
                (symbol, timeframe),
            ).fetchone()
        if row is None:
            return None
        return PaperState(
            symbol=row["symbol"],
            timeframe=row["timeframe"],
            last_ts=row["last_ts"],
            balance=Decimal(row["balance"]),
            day_start_ts=row["day_start_ts"],
            day_start_equity=Decimal(row["day_start_equity"]),
        )

    def save_paper_state(
        self, state: PaperState, connection: sqlite3.Connection | None = None
    ) -> None:
        """Сохранить чекпоинт: обработанная свеча, баланс и база дневного лимита."""

        with self._use(connection) as active:
            active.execute(
                """INSERT OR REPLACE INTO paper_state
                (symbol,timeframe,last_ts,balance,day_start_ts,day_start_equity)
                VALUES (?,?,?,?,?,?)""",
                (
                    state.symbol, state.timeframe, state.last_ts, str(state.balance),
                    state.day_start_ts, str(state.day_start_equity),
                ),
            )

    def realized_pnl_since(self, since_ts: int, symbol: str) -> Decimal:
        """Реализованный PnL по символу за период начиная с указанного времени."""

        with self.session() as connection:
            rows = connection.execute(
                """SELECT pnl FROM paper_trades
                WHERE symbol=? AND exit_ts>=? AND pnl IS NOT NULL""",
                (symbol, since_ts),
            ).fetchall()
        return sum((Decimal(row["pnl"]) for row in rows), Decimal(0))

    def save_news_items(self, items: Iterable[tuple[int, str, str, str, str, int]]) -> int:
        """Сохранить новости, игнорируя уже известные ссылки."""

        values = list(items)
        with self.session() as connection:
            connection.executemany(
                """INSERT OR IGNORE INTO news_items
                (ts,source,url,title,summary,relevance) VALUES (?,?,?,?,?,?)""",
                values,
            )
        return len(values)

    def save_digest(self, date: str, content: str, sent_ts: int | None = None) -> None:
        """Сохранить текстовый дайджест за дату (UTC, формат YYYY-MM-DD)."""

        with self.session() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO digests (date,content,sent_ts) VALUES (?,?,?)",
                (date, content, sent_ts),
            )
