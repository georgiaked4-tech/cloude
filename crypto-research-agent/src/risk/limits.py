"""Риск-модуль. Применяется до открытия любой позиции — и в бэктесте, и в paper-режиме.

Все расчёты в Decimal. Плечо отсутствует, только спот.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from src.core.config import RiskConfig

HUNDRED = Decimal("100")


@dataclass(frozen=True)
class RiskDecision:
    """Результат проверки лимитов: разрешено ли открывать позицию и почему нет."""

    allowed: bool
    reason: str = ""


def utc_day(ts_ms: int) -> str:
    """Дата UTC (YYYY-MM-DD) для timestamp в миллисекундах."""
    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC).strftime("%Y-%m-%d")


class RiskManager:
    """Проверяет лимиты и считает размер позиции, стоп и тейк."""

    def __init__(self, config: RiskConfig) -> None:
        self.config = config
        self._day: str | None = None
        self._day_start_balance: Decimal = config.initial_balance
        self._day_realized_pnl: Decimal = Decimal("0")
        self._blocked_until_next_day = False

    @property
    def day_realized_pnl(self) -> Decimal:
        """Реализованный PnL за текущий день UTC."""
        return self._day_realized_pnl

    @property
    def blocked(self) -> bool:
        """Достигнут ли дневной лимит убытка."""
        return self._blocked_until_next_day

    def start_day_if_needed(self, ts_ms: int, balance: Decimal) -> bool:
        """Сбрасывает дневные счётчики при переходе на новый день UTC.

        Возвращает True, если день сменился.
        """
        day = utc_day(ts_ms)
        if self._day == day:
            return False
        self._day = day
        self._day_start_balance = balance
        self._day_realized_pnl = Decimal("0")
        self._blocked_until_next_day = False
        return True

    def daily_loss_limit_value(self) -> Decimal:
        """Абсолютный дневной лимит убытка.

        Формула: баланс на начало дня * daily_loss_limit_pct / 100.
        """
        return self._day_start_balance * self.config.daily_loss_limit_pct / HUNDRED

    def register_trade_result(self, ts_ms: int, pnl: Decimal, balance: Decimal) -> bool:
        """Учитывает результат закрытой сделки. Возвращает True, если лимит убытка достигнут.

        Лимит считается по сумме реализованного PnL за день: если суммарный убыток
        не меньше дневного лимита, новые позиции до следующего дня UTC не открываются.
        """
        self.start_day_if_needed(ts_ms, balance)
        self._day_realized_pnl += pnl
        limit = self.daily_loss_limit_value()
        if limit > 0 and self._day_realized_pnl <= -limit:
            self._blocked_until_next_day = True
        return self._blocked_until_next_day

    def position_size(self, balance: Decimal, price: Decimal) -> Decimal:
        """Размер позиции в базовой валюте.

        Формула: qty = (баланс * max_position_pct / 100) / цена входа.
        Доля депозита в одной позиции не превышает max_position_pct.
        """
        if price <= 0:
            raise ValueError("цена должна быть больше нуля")
        notional = balance * self.config.max_position_pct / HUNDRED
        return notional / price

    def stop_loss_price(self, entry_price: Decimal) -> Decimal:
        """Цена стоп-лосса для длинной позиции.

        Формула: entry * (1 - stop_loss_pct / 100).
        """
        return entry_price * (Decimal(1) - self.config.stop_loss_pct / HUNDRED)

    def take_profit_price(self, entry_price: Decimal) -> Decimal:
        """Цена тейк-профита для длинной позиции.

        Формула: entry * (1 + take_profit_pct / 100).
        """
        return entry_price * (Decimal(1) + self.config.take_profit_pct / HUNDRED)

    def check_can_open(
        self, ts_ms: int, balance: Decimal, open_positions: int, price: Decimal
    ) -> RiskDecision:
        """Полная проверка перед открытием позиции."""
        self.start_day_if_needed(ts_ms, balance)

        if self.config.stop_loss_pct <= 0 or self.config.take_profit_pct <= 0:
            return RiskDecision(False, "позиция без стоп-лосса или тейк-профита не открывается")
        if self._blocked_until_next_day:
            return RiskDecision(False, "достигнут дневной лимит убытка")
        if open_positions >= self.config.max_open_positions:
            return RiskDecision(False, "достигнут лимит одновременных позиций")
        if balance <= 0:
            return RiskDecision(False, "нулевой или отрицательный баланс")

        qty = self.position_size(balance, price)
        if qty <= 0:
            return RiskDecision(False, "рассчитанный размер позиции равен нулю")
        if qty * price > balance:
            return RiskDecision(False, "недостаточно свободных средств (плечо запрещено)")
        return RiskDecision(True)
