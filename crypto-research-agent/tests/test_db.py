"""Тесты схемы и операций с базой."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from src.core.db import connect, load_candles, save_candles, save_signal, set_signal_status


def test_candles_roundtrip_keeps_decimal(tmp_path: Path) -> None:
    """Цены возвращаются как Decimal без потери точности."""
    conn = connect(tmp_path / "test.db")
    save_candles(
        conn,
        "BTC/USDT",
        "1h",
        [
            (
                1_700_000_000_000,
                Decimal("1.10"),
                Decimal("2.20"),
                Decimal("0.90"),
                Decimal("1.05"),
                Decimal("10.5"),
            )
        ],
    )
    rows = load_candles(conn, "BTC/USDT", "1h")
    assert len(rows) == 1
    assert rows[0]["close"] == Decimal("1.05")
    assert isinstance(rows[0]["close"], Decimal)
    conn.close()


def test_signal_status_update(tmp_path: Path) -> None:
    """Статус сигнала обновляется."""
    conn = connect(tmp_path / "test.db")
    signal_id = save_signal(conn, 1, "BTC/USDT", "ema_cross", "buy", Decimal("100"), "тест", "new")
    set_signal_status(conn, signal_id, "opened")
    row = conn.execute("SELECT status FROM signals WHERE id = ?", (signal_id,)).fetchone()
    assert row["status"] == "opened"
    conn.close()
