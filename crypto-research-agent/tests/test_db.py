import gc
import sqlite3
from decimal import Decimal

from src.core.db import Database, PaperState


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
    assert database.realized_pnl_since(1500, "BTC/USDT") == Decimal("7.78")
    assert database.realized_pnl_since(2500, "BTC/USDT") == Decimal("0")
    assert database.realized_pnl_since(1500, "ETH/USDT") == Decimal("0")


def test_equity_snapshots_support_daily_limit_restore(tmp_path) -> None:
    database = make_db(tmp_path)
    database.record_equity(1000, Decimal("9000"), Decimal("1000"))
    database.record_equity(2000, Decimal("8500"), Decimal("1000"))
    assert database.latest_equity() == (2000, Decimal("8500"), Decimal("1000"))


def test_news_and_digest_are_stored_without_duplicates(tmp_path) -> None:
    database = make_db(tmp_path)
    rows = [(1, "src", "https://a", "Bitcoin ETF", "summary", 2)]
    database.save_news_items(rows)
    database.save_news_items(rows)
    database.save_digest("2026-01-01", "текст дайджеста")
    with database.session() as connection:
        assert connection.execute("SELECT COUNT(*) FROM news_items").fetchone()[0] == 1
        assert connection.execute("SELECT content FROM digests").fetchone()[0] == "текст дайджеста"


def test_paper_state_is_scoped_by_symbol_and_timeframe(tmp_path) -> None:
    database = make_db(tmp_path)
    btc = PaperState("BTC/USDT", "1h", 1000, Decimal("9000"), 0, Decimal("10000"))
    eth = PaperState("ETH/USDT", "1h", 2000, Decimal("7000"), 0, Decimal("8000"))
    database.save_paper_state(btc)
    database.save_paper_state(eth)
    # Чекпоинт второй пары не должен перетирать первую и наоборот.
    assert database.load_paper_state("BTC/USDT", "1h") == btc
    assert database.load_paper_state("ETH/USDT", "1h") == eth
    assert database.load_paper_state("BTC/USDT", "4h") is None


def test_paper_state_keeps_the_day_opening_baseline(tmp_path) -> None:
    database = make_db(tmp_path)
    state = PaperState("BTC/USDT", "1h", 1000, Decimal("9000"), 500, Decimal("10500"))
    database.save_paper_state(state)
    restored = database.load_paper_state("BTC/USDT", "1h")
    assert restored is not None
    # База дневного лимита хранится явно, а не восстанавливается из срезов equity.
    assert restored.day_start_equity == Decimal("10500")
    assert restored.day_start_ts == 500


def test_multi_statement_writes_share_one_transaction(tmp_path) -> None:
    database = make_db(tmp_path)
    with database.session() as connection:
        signal_id = database.insert_signal(
            1, "BTC/USDT", "ema_cross", "buy", Decimal("100"), "cross",
            status="opened", connection=connection,
        )
        database.open_paper_trade(
            signal_id, "BTC/USDT", "long", Decimal("2"), Decimal("100"), 1,
            Decimal("0.11"), connection=connection,
        )
        database.save_paper_state(
            PaperState("BTC/USDT", "1h", 1, Decimal("9800"), 0, Decimal("10000")),
            connection=connection,
        )
    assert len(database.load_open_paper_trades("BTC/USDT")) == 1
    state = database.load_paper_state("BTC/USDT", "1h")
    assert state is not None and state.balance == Decimal("9800")
