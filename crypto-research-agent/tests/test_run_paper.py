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


def make_rows(prices: list[str]) -> list[tuple]:
    """Свечи без теней: low = high = close, чтобы стоп срабатывал предсказуемо."""

    rows = []
    for index, price in enumerate(prices):
        value = Decimal(price)
        rows.append((START_TS + index * HOUR_MS, value, value, value, value, Decimal("1")))
    return rows


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


def run_once(monkeypatch, capsys, project, rows: list[tuple], now_ms: int) -> dict:
    """Выполнить один проход `run_paper` с подменённым источником свечей."""

    class FakeMarketDataClient:
        def __init__(self, _config) -> None:
            pass

        def fetch_ohlcv(self, symbol, timeframe, limit=500, since=None):
            return rows

    monkeypatch.chdir(project)
    monkeypatch.setattr(run_paper, "MarketDataClient", FakeMarketDataClient)
    monkeypatch.setattr(run_paper.time, "time", lambda: now_ms / 1000)
    monkeypatch.setattr(sys, "argv", ["run_paper.py", "--symbol", "BTC/USDT",
                                      "--timeframe", "1h", "--once"])
    run_paper.main()
    # На stdout идут и структурные логи, и итоговый отчёт; берём отчёт.
    output = capsys.readouterr().out
    return json.loads(output[output.index('{\n  "mode"'):])


def test_forming_candle_is_ignored(monkeypatch, capsys, project) -> None:
    rows = make_rows(PRICES)
    # Момент «сейчас» внутри последней свечи: она ещё формируется.
    result = run_once(monkeypatch, capsys, project, rows, rows[-1][0] + HOUR_MS - 1)
    assert result["last_candle_ts"] == rows[-2][0]
    assert result["closed_candles_processed"] == len(rows) - 1


def test_position_opens_once_and_survives_restart(monkeypatch, capsys, project) -> None:
    rows = make_rows(PRICES)
    now = rows[-1][0] + HOUR_MS
    first = run_once(monkeypatch, capsys, project, rows, now)
    assert first["last_signal"] == "buy"
    assert first["open_position"] is not None

    database = Database(project / "agent.db")
    open_trades = database.load_open_paper_trades("BTC/USDT")
    assert len(open_trades) == 1
    assert database.latest_equity()[0] == rows[-1][0]

    # Повторный запуск на тех же данных не должен открывать вторую позицию
    # и не должен заново реагировать на уже обработанный сигнал.
    second = run_once(monkeypatch, capsys, project, rows, now)
    assert second["closed_candles_processed"] == 0
    assert second["open_position"] == first["open_position"]
    assert len(database.load_open_paper_trades("BTC/USDT")) == 1
    assert second["balance"] == first["balance"]


def test_stop_loss_closes_restored_position(monkeypatch, capsys, project) -> None:
    rows = make_rows(PRICES)
    now = rows[-1][0] + HOUR_MS
    first = run_once(monkeypatch, capsys, project, rows, now)
    stop_price = Decimal(first["open_position"]["stop_price"])

    crash = Decimal(PRICES[-1]) * Decimal("0.5")
    assert crash < stop_price
    extended = rows + make_rows([str(crash)])
    extended[-1] = (rows[-1][0] + HOUR_MS, *extended[-1][1:])
    result = run_once(monkeypatch, capsys, project, extended, now + HOUR_MS)

    assert result["open_position"] is None
    assert result["action"] == "Позиция закрыта: stop_loss"
    database = Database(project / "agent.db")
    assert database.load_open_paper_trades("BTC/USDT") == []
    with database.session() as connection:
        row = connection.execute(
            "SELECT exit_reason, pnl FROM paper_trades WHERE exit_ts IS NOT NULL"
        ).fetchone()
    assert row["exit_reason"] == "stop_loss"
    assert Decimal(row["pnl"]) < 0
