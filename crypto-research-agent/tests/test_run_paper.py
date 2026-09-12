"""Сквозные проверки paper-режима без сетевых вызовов."""

import json
import sys
from decimal import Decimal

import pytest
import yaml

from scripts import run_paper
from src.core.db import Database

HOUR_MS = 3_600_000
START_TS = 1_700_000_000_000
# Пересечение EMA приходится ровно на последнюю свечу.
PRICES = ["300", "200", "100", "200", "400"]


def make_rows(prices: list[str], start_index: int = 0) -> list[tuple]:
    """Свечи без теней: open = high = low = close, чтобы стоп срабатывал предсказуемо."""

    rows = []
    for offset, price in enumerate(prices):
        value = Decimal(price)
        ts = START_TS + (start_index + offset) * HOUR_MS
        rows.append((ts, value, value, value, value, Decimal("1")))
    return rows


class FakeExchange:
    """Отдаёт свечи как CCXT: окно фиксированного размера, опционально от `since`."""

    def __init__(self, rows: list[tuple]) -> None:
        self.rows = rows
        self.calls: list[tuple[int | None, int]] = []

    def __call__(self, _config) -> "FakeExchange":
        return self

    def fetch_ohlcv(self, symbol, timeframe, limit=500, since=None):
        self.calls.append((since, limit))
        if since is None:
            return self.rows[-limit:]
        selected = [row for row in self.rows if row[0] >= since]
        return selected[:limit]


@pytest.fixture
def project(tmp_path):
    """Изолированный проект: свой config.yaml и своя база."""

    config = {
        "exchange": {"name": "bybit", "timeout_ms": 1000, "max_retries": 1,
                     "retry_base_seconds": "0.1"},
        "trading": {"symbols": ["BTC/USDT"], "timeframe": "1h", "initial_balance": "10000",
                    "taker_fee_pct": "0.055", "slippage_pct": "0.05"},
        "strategy": {"fast_ema": 2, "slow_ema": 3},
        "risk": {"max_position_pct": "2", "max_open_positions": 3,
                 "daily_loss_limit_pct": "3", "stop_loss_pct": "2", "take_profit_pct": "4"},
        "storage": {"database_path": "agent.db"},
        "logging": {"level": "INFO"},
        "news": {"feeds": [], "request_timeout_seconds": 1},
        "research": {"model": "claude-sonnet-5", "max_tokens": 100, "max_news_items": 10},
    }
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    return tmp_path


def run_once(monkeypatch, capsys, project, rows, now_ms, symbol="BTC/USDT") -> dict:
    """Выполнить один проход `run_paper` с подменённым источником свечей."""

    exchange = rows if isinstance(rows, FakeExchange) else FakeExchange(rows)
    monkeypatch.chdir(project)
    monkeypatch.setattr(run_paper, "MarketDataClient", exchange)
    monkeypatch.setattr(run_paper.time, "time", lambda: now_ms / 1000)
    monkeypatch.setattr(sys, "argv", ["run_paper.py", "--symbol", symbol, "--once"])
    run_paper.main()
    # На stdout идут и структурные логи, и итоговый отчёт; берём отчёт.
    output = capsys.readouterr().out
    return json.loads(output[output.index('{\n  "mode"'):])


def test_forming_candle_is_ignored(monkeypatch, capsys, project) -> None:
    rows = make_rows(PRICES)
    # Момент «сейчас» внутри последней свечи: она ещё формируется.
    result = run_once(monkeypatch, capsys, project, rows, rows[-1][0] + HOUR_MS - 1)
    assert result["last_candle_ts"] == rows[-2][0]


def test_first_run_trades_the_newest_candle_only(monkeypatch, capsys, project) -> None:
    rows = make_rows(PRICES)
    now = rows[-1][0] + HOUR_MS
    result = run_once(monkeypatch, capsys, project, rows, now)
    # История прогревает индикатор, но задним числом не отыгрывается.
    assert result["closed_candles_processed"] == 1
    assert result["last_signal"] == "buy"
    assert result["open_position"] is not None

    database = Database(project / "agent.db")
    assert len(database.load_open_paper_trades("BTC/USDT")) == 1
    state = database.load_paper_state("BTC/USDT", "1h")
    assert state is not None and state.last_ts == rows[-1][0]


def test_position_survives_restart_without_reopening(monkeypatch, capsys, project) -> None:
    rows = make_rows(PRICES)
    now = rows[-1][0] + HOUR_MS
    first = run_once(monkeypatch, capsys, project, rows, now)
    second = run_once(monkeypatch, capsys, project, rows, now)

    assert second["closed_candles_processed"] == 0
    assert second["open_position"] == first["open_position"]
    assert second["balance"] == first["balance"]
    database = Database(project / "agent.db")
    assert len(database.load_open_paper_trades("BTC/USDT")) == 1


def test_outage_longer_than_the_fetch_window_still_sees_the_stop(
    monkeypatch, capsys, project
) -> None:
    rows = make_rows(PRICES)
    now = rows[-1][0] + HOUR_MS
    first = run_once(monkeypatch, capsys, project, rows, now)
    stop_price = Decimal(first["open_position"]["stop_price"])

    # Планировщик молчал 205 свечей: стоп пробит на первой же из них, а дальше
    # цена вернулась выше стопа. Окно фиксированного размера этот бар потеряло бы.
    crash = str(stop_price * Decimal("0.5"))
    outage = make_rows([crash] + ["400"] * 204, start_index=len(PRICES))
    monkeypatch.setattr(run_paper, "PAGE_LIMIT", 50)
    exchange = FakeExchange(rows + outage)
    result = run_once(monkeypatch, capsys, project, exchange, outage[-1][0] + HOUR_MS)

    assert result["closed_candles_processed"] == len(outage)
    # Дозагрузка шла страницами от чекпоинта, а не одним последним окном.
    assert len(exchange.calls) > 1
    assert all(since is not None for since, _ in exchange.calls)

    database = Database(project / "agent.db")
    with database.session() as connection:
        rows_out = connection.execute(
            """SELECT exit_reason, exit_price, entry_price, pnl FROM paper_trades
            WHERE exit_ts IS NOT NULL"""
        ).fetchall()
    # Позиция, открытая до простоя, закрыта по стопу той самой пропущенной свечи.
    assert [row["exit_reason"] for row in rows_out] == ["stop_loss"]
    assert Decimal(rows_out[0]["pnl"]) < 0
    # Гэп ниже стопа исполняется по цене открытия, а не по недостижимому стопу.
    assert Decimal(rows_out[0]["exit_price"]) < stop_price


def test_second_symbol_does_not_inherit_the_first_checkpoint(
    monkeypatch, capsys, project
) -> None:
    rows = make_rows(PRICES)
    now = rows[-1][0] + HOUR_MS
    run_once(monkeypatch, capsys, project, rows, now, symbol="BTC/USDT")
    second = run_once(monkeypatch, capsys, project, rows, now, symbol="ETH/USDT")

    # Общий чекпоинт заставил бы второй символ считать свои свечи обработанными.
    assert second["closed_candles_processed"] == 1
    assert second["last_signal"] == "buy"
    database = Database(project / "agent.db")
    assert database.load_paper_state("ETH/USDT", "1h") is not None
    assert len(database.load_open_paper_trades("ETH/USDT")) == 1
