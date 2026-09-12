"""Тесты риск-модуля: каждый лимит покрыт отдельно."""

from __future__ import annotations

from decimal import Decimal

from src.core.config import RiskConfig
from src.risk.limits import RiskManager, utc_day

DAY_MS = 24 * 60 * 60 * 1000
TS = 1_700_000_000_000


def test_position_size_respects_max_position_pct(risk_config: RiskConfig) -> None:
    """Размер позиции — ровно max_position_pct от депозита."""
    risk = RiskManager(risk_config)
    qty = risk.position_size(Decimal("10000"), Decimal("100"))
    # 2% от 10000 = 200; 200 / 100 = 2 единицы базовой валюты.
    assert qty == Decimal("2")


def test_max_open_positions_blocks_extra_position(risk_config: RiskConfig) -> None:
    """При достижении лимита одновременных позиций новая не открывается."""
    risk = RiskManager(risk_config)
    allowed = risk.check_can_open(TS, Decimal("10000"), open_positions=2, price=Decimal("100"))
    blocked = risk.check_can_open(TS, Decimal("10000"), open_positions=3, price=Decimal("100"))
    assert allowed.allowed is True
    assert blocked.allowed is False
    assert "одновременных позиций" in blocked.reason


def test_daily_loss_limit_blocks_until_next_day(risk_config: RiskConfig) -> None:
    """При достижении дневного убытка вход закрыт до следующего дня UTC."""
    risk = RiskManager(risk_config)
    risk.start_day_if_needed(TS, Decimal("10000"))
    # Лимит: 3% от 10000 = 300. Убыток 300 достигает лимита.
    risk.register_trade_result(TS, Decimal("-300"), Decimal("9700"))
    assert risk.blocked is True
    assert risk.check_can_open(TS, Decimal("9700"), 0, Decimal("100")).allowed is False

    # Следующий день UTC — счётчики сброшены, торговля снова разрешена.
    next_day = TS + DAY_MS
    assert risk.check_can_open(next_day, Decimal("9700"), 0, Decimal("100")).allowed is True
    assert risk.blocked is False


def test_daily_loss_limit_not_triggered_below_threshold(risk_config: RiskConfig) -> None:
    """Убыток меньше лимита торговлю не останавливает."""
    risk = RiskManager(risk_config)
    risk.start_day_if_needed(TS, Decimal("10000"))
    risk.register_trade_result(TS, Decimal("-299"), Decimal("9701"))
    assert risk.blocked is False


def test_position_requires_stop_and_take(risk_config: RiskConfig) -> None:
    """Без стоп-лосса или тейк-профита позиция не открывается."""
    no_stop = risk_config.model_copy(update={"stop_loss_pct": Decimal("0")})
    no_take = risk_config.model_copy(update={"take_profit_pct": Decimal("0")})
    balance = Decimal("10000")
    price = Decimal("100")
    assert RiskManager(no_stop).check_can_open(TS, balance, 0, price).allowed is False
    assert RiskManager(no_take).check_can_open(TS, balance, 0, price).allowed is False


def test_stop_and_take_prices(risk_config: RiskConfig) -> None:
    """Цены стопа и тейка считаются от цены входа."""
    risk = RiskManager(risk_config)
    assert risk.stop_loss_price(Decimal("100")) == Decimal("98.500")
    assert risk.take_profit_price(Decimal("100")) == Decimal("103.00")


def test_no_leverage(risk_config: RiskConfig) -> None:
    """Позиция никогда не превышает свободный баланс — плечо запрещено."""
    leveraged = risk_config.model_copy(update={"max_position_pct": Decimal("150")})
    decision = RiskManager(leveraged).check_can_open(TS, Decimal("10000"), 0, Decimal("100"))
    assert decision.allowed is False
    assert "плечо" in decision.reason


def test_zero_balance_blocks_entry(risk_config: RiskConfig) -> None:
    """При нулевом балансе вход запрещён."""
    risk = RiskManager(risk_config)
    assert risk.check_can_open(TS, Decimal("0"), 0, Decimal("100")).allowed is False


def test_utc_day_is_utc() -> None:
    """День считается в UTC, а не в локальной зоне."""
    assert utc_day(0) == "1970-01-01"
