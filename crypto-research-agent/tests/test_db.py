import gc
import sqlite3
from decimal import Decimal

from src.core.db import Database


def make_db(tmp_path) -> Database:
    database = Database(tmp_path / "agent.db")
    database.initialize()
    return database


def test_connections_are_closed_after_every_operation(tmp_path) -> None:
    database = make_db(tmp_path)
    database.upsert_candles(
        "BTC/USDT", "1h", [(1, Decimal(1), Decimal(1), Decimal(1), Decimal(1), Decimal(1))]
    )
    database.load_candles("BTC/USDT", "1h")
    gc.collect()
    alive = 0
    for connection in [o for o in gc.get_objects() if isinstance(o, sqlite3.Connection)]:
        try:
            connection.execute("SELECT 1")
            alive += 1
        except sqlite3.ProgrammingError:
            pass
    assert alive == 0


def test_signal_and_trade_lifecycle_is_persisted(tmp_path) -> None:
    database = make_db(tmp_path)
    signal_id = database.insert_signal(
        1000, "BTC/USDT", "ema_cross", "buy", Decimal("100"), "cross"
    )
    trade_id = database.open_paper_trade(
        signal_id, "BTC/USDT", "long", Decimal("2"), Decimal("100"), 1000, Decimal("0.11")
    )
    database.set_signal_status(signal_id, "opened")

    open_trades = database.load_open_paper_trades("BTC/USDT")
    assert [trade.trade_id for trade in open_trades] == [trade_id]
    assert open_trades[0].entry_price == Decimal("100")

    database.close_paper_trade(
        trade_id, Decimal("104"), 2000, Decimal("0.22"), Decimal("7.78"),
        Decimal("3.88"), "take_profit",
    )
    assert database.load_open_paper_trades("BTC/USDT") == []
    assert database.realized_pnl_since(1500) == Decimal("7.78")
    assert database.realized_pnl_since(2500) == Decimal("0")


def test_equity_snapshots_support_daily_limit_restore(tmp_path) -> None:
    database = make_db(tmp_path)
    database.record_equity(1000, Decimal("9000"), Decimal("1000"))
    database.record_equity(2000, Decimal("8500"), Decimal("1000"))
    assert database.latest_equity() == (2000, Decimal("8500"), Decimal("1000"))
    # Капитал на начало дня = баланс + оценка позиций в первом срезе после границы.
    assert database.equity_at_day_start(500) == Decimal("10000")
    assert database.equity_at_day_start(5000) is None


def test_news_and_digest_are_stored_without_duplicates(tmp_path) -> None:
    database = make_db(tmp_path)
    rows = [(1, "src", "https://a", "Bitcoin ETF", "summary", 2)]
    database.save_news_items(rows)
    database.save_news_items(rows)
    database.save_digest("2026-01-01", "текст дайджеста")
    with database.session() as connection:
        assert connection.execute("SELECT COUNT(*) FROM news_items").fetchone()[0] == 1
        assert connection.execute("SELECT content FROM digests").fetchone()[0] == "текст дайджеста"
