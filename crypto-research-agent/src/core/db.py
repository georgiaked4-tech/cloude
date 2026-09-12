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
"""


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
    ) -> int:
        """Записать сигнал стратегии и вернуть его идентификатор."""

        with self.session() as connection:
            cursor = connection.execute(
                """INSERT INTO signals (ts,symbol,strategy,side,price,reason,status)
                VALUES (?,?,?,?,?,?,?)""",
                (ts, symbol, strategy, side, str(price), reason, status),
            )
        return int(cursor.lastrowid or 0)

    def set_signal_status(self, signal_id: int, status: str) -> None:
        """Обновить статус сигнала: new | opened | skipped."""

        with self.session() as connection:
            connection.execute(
                "UPDATE signals SET status=? WHERE id=?", (status, signal_id)
            )

    def open_paper_trade(
        self,
        signal_id: int,
        symbol: str,
        side: str,
        qty: Decimal,
        entry_price: Decimal,
        entry_ts: int,
        entry_fee: Decimal,
    ) -> int:
        """Создать строку сделки без цены выхода — это открытая позиция."""

        with self.session() as connection:
            cursor = connection.execute(
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
    ) -> None:
        """Дописать в открытую сделку цену выхода, суммарную комиссию и PnL."""

        with self.session() as connection:
            connection.execute(
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

    def record_equity(self, ts: int, balance: Decimal, open_value: Decimal) -> None:
        """Сохранить срез капитала: свободный баланс и оценку открытых позиций."""

        with self.session() as connection:
            connection.execute(
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

    def equity_at_day_start(self, day_start_ts: int) -> Decimal | None:
        """Капитал в первом срезе текущего UTC-дня — база для дневного лимита."""

        with self.session() as connection:
            row = connection.execute(
                """SELECT balance,open_value FROM equity
                WHERE ts>=? ORDER BY ts LIMIT 1""",
                (day_start_ts,),
            ).fetchone()
        if row is None:
            return None
        return Decimal(row["balance"]) + Decimal(row["open_value"])

    def realized_pnl_since(self, since_ts: int) -> Decimal:
        """Сумма реализованного PnL по сделкам, закрытым не раньше указанного времени."""

        with self.session() as connection:
            rows = connection.execute(
                "SELECT pnl FROM paper_trades WHERE exit_ts>=? AND pnl IS NOT NULL",
                (since_ts,),
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
