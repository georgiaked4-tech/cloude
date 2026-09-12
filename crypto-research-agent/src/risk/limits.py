"""Детерминированные риск-лимиты для бэктеста и paper broker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from src.core.config import RiskConfig

HUNDRED = Decimal("100")
MS_IN_SECOND = 1000


def utc_day_start_ms(ts_ms: int) -> int:
    """Начало UTC-суток для метки времени в миллисекундах.

    Дневной лимит убытка считается по календарным UTC-суткам, поэтому граница
    дня вычисляется один раз здесь и переиспользуется бэктестом и paper-режимом.
    """

    moment = datetime.fromtimestamp(ts_ms / MS_IN_SECOND, tz=UTC)
    day_start = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(day_start.timestamp()) * MS_IN_SECOND


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str


class RiskManager:
    """Проверяет лимиты до любой имитации открытия позиции."""

    def __init__(self, config: RiskConfig) -> None:
        self.config = config

    def check_open(
        self, day_start_balance: Decimal, daily_pnl: Decimal, open_positions: int
    ) -> RiskDecision:
        """Запретить вход при превышении количества позиций или дневного убытка."""

        if open_positions >= self.config.max_open_positions:
            return RiskDecision(False, "Достигнут лимит открытых позиций")
        # Лимит убытка = баланс на начало UTC-дня × процент / 100.
        loss_limit = day_start_balance * self.config.daily_loss_limit_pct / HUNDRED
        if daily_pnl <= -loss_limit:
            return RiskDecision(False, "Достигнут дневной лимит убытка")
        return RiskDecision(True, "Риск-лимиты соблюдены")

    def position_notional(self, balance: Decimal) -> Decimal:
        """Размер позиции = доступный баланс × max_position_pct / 100."""

        return balance * self.config.max_position_pct / HUNDRED

    def exit_prices(self, entry_price: Decimal) -> tuple[Decimal, Decimal]:
        """Стоп/тейк = цена входа × (1 ∓ соответствующий процент / 100)."""

        stop = entry_price * (Decimal(1) - self.config.stop_loss_pct / HUNDRED)
        take = entry_price * (Decimal(1) + self.config.take_profit_pct / HUNDRED)
        return stop, take

