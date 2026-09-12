"""SQLite: схема, подключение, простые операции чтения и записи.

Все денежные величины хранятся как TEXT — строковое представление Decimal.
Время — timestamp в миллисекундах UTC (int).
"""

from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS candles(
    symbol TEXT, timeframe TEXT, ts INTEGER, open TEXT, high TEXT,
    low TEXT, close TEXT, volume TEXT, PRIMARY KEY(symbol, timeframe, ts));

CREATE TABLE IF NOT EXISTS signals(
    id INTEGER PRIMARY KEY, ts INTEGER, symbol TEXT, strategy TEXT, side TEXT,
    price TEXT, reason TEXT, status TEXT);

CREATE TABLE IF NOT EXISTS paper_trades(
    id INTEGER PRIMARY KEY, signal_id INTEGER, symbol TEXT, side TEXT,
    qty TEXT, entry_price TEXT, entry_ts INTEGER, exit_price TEXT,
    exit_ts INTEGER, fee TEXT, pnl TEXT, pnl_pct TEXT, exit_reason TEXT);

CREATE TABLE IF NOT EXISTS equity(ts INTEGER PRIMARY KEY, balance TEXT, open_value TEXT);

CREATE TABLE IF NOT EXISTS news_items(
    id INTEGER PRIMARY KEY, ts INTEGER, source TEXT, url TEXT UNIQUE,
    title TEXT, summary TEXT, relevance INTEGER);

CREATE TABLE IF NOT EXISTS digests(date TEXT PRIMARY KEY, content TEXT, sent_ts INTEGER);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    """Открывает подключение и создаёт схему, если её нет."""
    db_path = Path(path)
    if db_path.parent != Path(""):
        db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Создаёт таблицы согласно §6 правил проекта."""
    conn.executescript(SCHEMA)
    conn.commit()


def save_candles(
    conn: sqlite3.Connection, symbol: str, timeframe: str, candles: list[tuple]
) -> int:
    """Сохраняет свечи. candles: (ts, open, high, low, close, volume) с Decimal-значениями."""
    rows = [
        (symbol, timeframe, int(ts), str(o), str(h), str(low), str(c), str(v))
        for ts, o, h, low, c, v in candles
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO candles(symbol, timeframe, ts, open, high, low, close, volume)"
        " VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def load_candles(
    conn: sqlite3.Connection,
    symbol: str,
    timeframe: str,
    start_ts: int | None = None,
    end_ts: int | None = None,
) -> list[dict]:
    """Читает свечи в хронологическом порядке, цены — Decimal."""
    query = "SELECT * FROM candles WHERE symbol = ? AND timeframe = ?"
    params: list[object] = [symbol, timeframe]
    if start_ts is not None:
        query += " AND ts >= ?"
        params.append(start_ts)
    if end_ts is not None:
        query += " AND ts <= ?"
        params.append(end_ts)
    query += " ORDER BY ts ASC"
    rows = conn.execute(query, params).fetchall()
    return [
        {
            "symbol": row["symbol"],
            "timeframe": row["timeframe"],
            "ts": int(row["ts"]),
            "open": Decimal(row["open"]),
            "high": Decimal(row["high"]),
            "low": Decimal(row["low"]),
            "close": Decimal(row["close"]),
            "volume": Decimal(row["volume"]),
        }
        for row in rows
    ]


def save_signal(
    conn: sqlite3.Connection,
    ts: int,
    symbol: str,
    strategy: str,
    side: str,
    price: Decimal,
    reason: str,
    status: str,
) -> int:
    """Записывает сигнал. status: new|opened|skipped."""
    cursor = conn.execute(
        "INSERT INTO signals(ts, symbol, strategy, side, price, reason, status)"
        " VALUES(?, ?, ?, ?, ?, ?, ?)",
        (int(ts), symbol, strategy, side, str(price), reason, status),
    )
    conn.commit()
    return int(cursor.lastrowid)


def set_signal_status(conn: sqlite3.Connection, signal_id: int, status: str) -> None:
    """Обновляет статус сигнала."""
    conn.execute("UPDATE signals SET status = ? WHERE id = ?", (status, signal_id))
    conn.commit()


def save_trade(conn: sqlite3.Connection, trade: dict) -> int:
    """Сохраняет закрытую или открытую бумажную сделку."""
    cursor = conn.execute(
        "INSERT INTO paper_trades(signal_id, symbol, side, qty, entry_price, entry_ts,"
        " exit_price, exit_ts, fee, pnl, pnl_pct, exit_reason)"
        " VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            trade.get("signal_id"),
            trade["symbol"],
            trade["side"],
            str(trade["qty"]),
            str(trade["entry_price"]),
            int(trade["entry_ts"]),
            None if trade.get("exit_price") is None else str(trade["exit_price"]),
            None if trade.get("exit_ts") is None else int(trade["exit_ts"]),
            str(trade.get("fee", Decimal("0"))),
            None if trade.get("pnl") is None else str(trade["pnl"]),
            None if trade.get("pnl_pct") is None else str(trade["pnl_pct"]),
            trade.get("exit_reason"),
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def save_equity(conn: sqlite3.Connection, ts: int, balance: Decimal, open_value: Decimal) -> None:
    """Пишет точку кривой капитала."""
    conn.execute(
        "INSERT OR REPLACE INTO equity(ts, balance, open_value) VALUES(?, ?, ?)",
        (int(ts), str(balance), str(open_value)),
    )
    conn.commit()


def save_news_item(
    conn: sqlite3.Connection,
    ts: int,
    source: str,
    url: str,
    title: str,
    summary: str,
    relevance: int,
) -> bool:
    """Сохраняет новость. Возвращает False, если такой url уже есть."""
    cursor = conn.execute(
        "INSERT OR IGNORE INTO news_items(ts, source, url, title, summary, relevance)"
        " VALUES(?, ?, ?, ?, ?, ?)",
        (int(ts), source, url, title, summary, int(relevance)),
    )
    conn.commit()
    return cursor.rowcount > 0


def load_recent_news(conn: sqlite3.Connection, since_ts: int, min_relevance: int = 1) -> list[dict]:
    """Новости не старше since_ts с достаточной релевантностью."""
    rows = conn.execute(
        "SELECT * FROM news_items WHERE ts >= ? AND relevance >= ? ORDER BY ts DESC",
        (int(since_ts), int(min_relevance)),
    ).fetchall()
    return [dict(row) for row in rows]


def save_digest(conn: sqlite3.Connection, date: str, content: str, sent_ts: int | None) -> None:
    """Сохраняет дайджест за дату (YYYY-MM-DD, UTC)."""
    conn.execute(
        "INSERT OR REPLACE INTO digests(date, content, sent_ts) VALUES(?, ?, ?)",
        (date, content, None if sent_ts is None else int(sent_ts)),
    )
    conn.commit()
