"""Спотовый paper broker без интеграции с приватными API биржи."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.core.config import TradingConfig
from src.risk.limits import HUNDRED, RiskManager
from src.strategy.base import Signal


@dataclass
class PaperPosition:
    signal_id: int
    symbol: str
    qty: Decimal
    entry_price: Decimal
    entry_ts: int
    entry_fee: Decimal
    stop_price: Decimal
    take_price: Decimal


@dataclass(frozen=True)
class PaperTrade:
    signal_id: int
    symbol: str
    side: str
    qty: Decimal
    entry_price: Decimal
    entry_ts: int
    exit_price: Decimal
    exit_ts: int
    fee: Decimal
    pnl: Decimal
    pnl_pct: Decimal
    exit_reason: str


class PaperBroker:
    """Имитирует только long spot-позиции и учитывает все торговые издержки."""

    def __init__(self, trading: TradingConfig, risk: RiskManager) -> None:
        self.trading = trading
        self.risk = risk
        self.balance = trading.initial_balance
        self.day_start_balance = trading.initial_balance
        self.daily_pnl = Decimal(0)
        self.positions: dict[str, PaperPosition] = {}
        self.closed_trades: list[PaperTrade] = []

    def _fee(self, notional: Decimal) -> Decimal:
        """Комиссия = номинал сделки × taker_fee_pct / 100."""

        return notional * self.trading.taker_fee_pct / HUNDRED

    def _entry_price(self, market_price: Decimal) -> Decimal:
        """Для покупки ухудшаем цену вверх на процент проскальзывания."""

        return market_price * (Decimal(1) + self.trading.slippage_pct / HUNDRED)

    def _exit_price(self, market_price: Decimal) -> Decimal:
        """Для продажи ухудшаем цену вниз на процент проскальзывания."""

        return market_price * (Decimal(1) - self.trading.slippage_pct / HUNDRED)

    def open_long(self, signal_id: int, signal: Signal) -> tuple[bool, str]:
        """Открыть виртуальную long-позицию после всех риск-проверок."""

        if signal.side != "buy":
            return False, "Для открытия требуется buy-сигнал"
        if signal.symbol in self.positions:
            return False, "Позиция по символу уже открыта"
        decision = self.risk.check_open(
            self.day_start_balance, self.daily_pnl, len(self.positions)
        )
        if not decision.allowed:
            return False, decision.reason

        effective_price = self._entry_price(signal.price)
        notional = self.risk.position_notional(self.balance)
        entry_fee = self._fee(notional)
        if notional + entry_fee > self.balance:
            return False, "Недостаточно виртуального баланса"
        # Количество = выделенный на позицию номинал / цена с проскальзыванием.
        qty = notional / effective_price
        stop, take = self.risk.exit_prices(effective_price)
        self.balance -= notional + entry_fee
        self.positions[signal.symbol] = PaperPosition(
            signal_id, signal.symbol, qty, effective_price, signal.ts,
            entry_fee, stop, take,
        )
        return True, "Виртуальная позиция открыта"

    def close_long(
        self, symbol: str, market_price: Decimal, ts: int, reason: str
    ) -> PaperTrade:
        """Закрыть виртуальную позицию и зафиксировать чистый PnL."""

        position = self.positions.pop(symbol)
        effective_price = self._exit_price(market_price)
        proceeds = position.qty * effective_price
        exit_fee = self._fee(proceeds)
        total_fee = position.entry_fee + exit_fee
        # Чистый PnL = (выход − вход) × количество − обе комиссии.
        pnl = (effective_price - position.entry_price) * position.qty - total_fee
        invested = position.entry_price * position.qty + position.entry_fee
        pnl_pct = pnl / invested * HUNDRED
        self.balance += proceeds - exit_fee
        self.daily_pnl += pnl
        trade = PaperTrade(
            position.signal_id, symbol, "long", position.qty, position.entry_price,
            position.entry_ts, effective_price, ts, total_fee, pnl, pnl_pct, reason,
        )
        self.closed_trades.append(trade)
        return trade

    def process_price(
        self,
        symbol: str,
        candle_open: Decimal,
        candle_low: Decimal,
        candle_high: Decimal,
        ts: int,
    ) -> PaperTrade | None:
        """Проверить обязательные stop-loss/take-profit; при конфликте выбрать худший исход."""

        position = self.positions.get(symbol)
        if position is None:
            return None
        if candle_low <= position.stop_price:
            # Если свеча открылась гэпом ниже стопа, исполниться по стопу
            # невозможно: цена такого уровня в этой свече не торговалась.
            # Берём худшую из двух — цену открытия.
            fill = min(position.stop_price, candle_open)
            return self.close_long(symbol, fill, ts, "stop_loss")
        if candle_high >= position.take_price:
            # Гэп вверх в пользу позиции не засчитываем: тейк исполняется по
            # своей цене, иначе бэктест присваивал бы себе случайную прибыль.
            return self.close_long(symbol, position.take_price, ts, "take_profit")
        return None

    def equity(self, market_prices: dict[str, Decimal]) -> Decimal:
        """Капитал = свободный баланс + открытые позиции по текущей цене."""

        open_value = sum(
            (
                position.qty * market_prices[symbol]
                for symbol, position in self.positions.items()
                if symbol in market_prices
            ),
            Decimal(0),
        )
        return self.balance + open_value

    def restore_position(
        self,
        signal_id: int,
        symbol: str,
        qty: Decimal,
        entry_price: Decimal,
        entry_ts: int,
        entry_fee: Decimal,
    ) -> PaperPosition:
        """Восстановить открытую позицию из БД между запусками paper-режима.

        Стоп и тейк не хранятся в базе: они детерминированно выводятся из цены
        входа и процентов риска, поэтому пересчитываются тем же RiskManager.
        """

        stop, take = self.risk.exit_prices(entry_price)
        position = PaperPosition(
            signal_id, symbol, qty, entry_price, entry_ts, entry_fee, stop, take
        )
        self.positions[symbol] = position
        return position

    def set_state(
        self, balance: Decimal, day_start_balance: Decimal, daily_pnl: Decimal
    ) -> None:
        """Задать баланс и дневные счётчики, восстановленные из истории."""

        self.balance = balance
        self.day_start_balance = day_start_balance
        self.daily_pnl = daily_pnl

    def reset_utc_day(self, marked_equity: Decimal | None = None) -> None:
        """Начать новый UTC-день и обнулить счётчик реализованного дневного PnL.

        База дневного лимита — капитал целиком, поэтому при открытых позициях
        сюда передаётся оценка капитала, а не один свободный баланс.
        """

        self.day_start_balance = marked_equity if marked_equity is not None else self.balance
        self.daily_pnl = Decimal(0)
