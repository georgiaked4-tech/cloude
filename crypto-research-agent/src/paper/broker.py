"""Симулятор исполнения (paper). Реальных ордеров не отправляет — только read-only рынок.

Один и тот же брокер используется бэктестом и paper-режимом.
Комиссия и проскальзывание учитываются всегда, значения берутся из конфига.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.core.config import CostsConfig
from src.risk.limits import RiskManager
from src.strategy.base import SIDE_BUY, Candle, Signal

HUNDRED = Decimal("100")

EXIT_STOP_LOSS = "stop_loss"
EXIT_TAKE_PROFIT = "take_profit"
EXIT_SIGNAL = "signal"
EXIT_FORCED = "forced_close"


@dataclass
class Position:
    """Открытая длинная позиция. Позиция без стопа и тейка не создаётся."""

    symbol: str
    qty: Decimal
    entry_price: Decimal
    entry_ts: int
    stop_price: Decimal
    take_price: Decimal
    entry_fee: Decimal
    signal_id: int | None = None


@dataclass
class Trade:
    """Закрытая сделка со всеми издержками."""

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
    signal_id: int | None = None
    gross_pnl: Decimal = Decimal("0")

    def as_row(self) -> dict:
        """Представление для таблицы paper_trades."""
        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "entry_price": self.entry_price,
            "entry_ts": self.entry_ts,
            "exit_price": self.exit_price,
            "exit_ts": self.exit_ts,
            "fee": self.fee,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "exit_reason": self.exit_reason,
        }


class PaperBroker:
    """Учитывает баланс, позиции и издержки. Ордера на биржу не отправляются никогда."""

    def __init__(self, balance: Decimal, costs: CostsConfig, risk: RiskManager) -> None:
        self.initial_balance = balance
        self.balance = balance
        self.costs = costs
        self.risk = risk
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []
        self.equity_curve: list[tuple[int, Decimal, Decimal]] = []

    # --- издержки -----------------------------------------------------------

    def buy_price_with_slippage(self, price: Decimal) -> Decimal:
        """Цена покупки хуже рыночной на величину проскальзывания.

        Формула: price * (1 + slippage_pct / 100).
        """
        return price * (Decimal(1) + self.costs.slippage_pct / HUNDRED)

    def sell_price_with_slippage(self, price: Decimal) -> Decimal:
        """Цена продажи хуже рыночной на величину проскальзывания.

        Формула: price * (1 - slippage_pct / 100).
        """
        return price * (Decimal(1) - self.costs.slippage_pct / HUNDRED)

    def fee(self, qty: Decimal, price: Decimal) -> Decimal:
        """Комиссия тейкера.

        Формула: qty * price * taker_fee_pct / 100.
        """
        return qty * price * self.costs.taker_fee_pct / HUNDRED

    # --- позиции ------------------------------------------------------------

    @property
    def open_positions(self) -> int:
        """Количество открытых позиций."""
        return len(self.positions)

    def open_value(self, prices: dict[str, Decimal]) -> Decimal:
        """Оценка открытых позиций по последним ценам.

        Формула: сумма qty * последняя цена по каждой позиции.
        """
        total = Decimal("0")
        for symbol, position in self.positions.items():
            price = prices.get(symbol, position.entry_price)
            total += position.qty * price
        return total

    def equity(self, prices: dict[str, Decimal]) -> Decimal:
        """Капитал = свободный баланс + оценка открытых позиций."""
        return self.balance + self.open_value(prices)

    def try_open(self, signal: Signal, signal_id: int | None = None) -> Position | None:
        """Открывает длинную позицию, если риск-модуль разрешил. Иначе возвращает None."""
        if signal.side != SIDE_BUY:
            return None
        if signal.symbol in self.positions:
            return None

        entry_price = self.buy_price_with_slippage(signal.price)
        decision = self.risk.check_can_open(
            ts_ms=signal.ts,
            balance=self.balance,
            open_positions=self.open_positions,
            price=entry_price,
        )
        if not decision.allowed:
            return None

        qty = self.risk.position_size(self.balance, entry_price)
        entry_fee = self.fee(qty, entry_price)
        cost = qty * entry_price + entry_fee
        if cost > self.balance:
            return None

        self.balance -= cost
        position = Position(
            symbol=signal.symbol,
            qty=qty,
            entry_price=entry_price,
            entry_ts=signal.ts,
            stop_price=self.risk.stop_loss_price(entry_price),
            take_price=self.risk.take_profit_price(entry_price),
            entry_fee=entry_fee,
            signal_id=signal_id,
        )
        self.positions[signal.symbol] = position
        return position

    def close(self, symbol: str, ts: int, price: Decimal, reason: str) -> Trade | None:
        """Закрывает позицию по указанной цене с учётом проскальзывания и комиссии."""
        position = self.positions.pop(symbol, None)
        if position is None:
            return None

        exit_price = self.sell_price_with_slippage(price)
        exit_fee = self.fee(position.qty, exit_price)
        self.balance += position.qty * exit_price - exit_fee

        # PnL до комиссий: (цена выхода - цена входа) * количество.
        gross_pnl = (exit_price - position.entry_price) * position.qty
        total_fee = position.entry_fee + exit_fee
        # PnL после комиссий: из валового результата вычитаются комиссии входа и выхода.
        pnl = gross_pnl - total_fee
        # Доходность сделки в процентах от вложенной суммы.
        invested = position.entry_price * position.qty
        pnl_pct = (pnl / invested * HUNDRED) if invested > 0 else Decimal("0")

        trade = Trade(
            symbol=symbol,
            side="long",
            qty=position.qty,
            entry_price=position.entry_price,
            entry_ts=position.entry_ts,
            exit_price=exit_price,
            exit_ts=ts,
            fee=total_fee,
            pnl=pnl,
            pnl_pct=pnl_pct,
            exit_reason=reason,
            signal_id=position.signal_id,
            gross_pnl=gross_pnl,
        )
        self.trades.append(trade)
        self.risk.register_trade_result(ts, pnl, self.balance)
        return trade

    def on_candle(self, symbol: str, candle: Candle) -> Trade | None:
        """Проверяет срабатывание стопа и тейка внутри свечи.

        Если в одной свече задеты обе границы, консервативно считаем,
        что первым сработал стоп-лосс.
        """
        position = self.positions.get(symbol)
        if position is None:
            return None
        if candle.low <= position.stop_price:
            return self.close(symbol, candle.ts, position.stop_price, EXIT_STOP_LOSS)
        if candle.high >= position.take_price:
            return self.close(symbol, candle.ts, position.take_price, EXIT_TAKE_PROFIT)
        return None

    def record_equity(self, ts: int, prices: dict[str, Decimal]) -> None:
        """Добавляет точку в кривую капитала."""
        self.equity_curve.append((ts, self.balance, self.open_value(prices)))

    def close_all(
        self, ts: int, prices: dict[str, Decimal], reason: str = EXIT_FORCED
    ) -> list[Trade]:
        """Закрывает все позиции — используется в конце бэктеста."""
        closed: list[Trade] = []
        for symbol in list(self.positions.keys()):
            price = prices.get(symbol, self.positions[symbol].entry_price)
            trade = self.close(symbol, ts, price, reason)
            if trade is not None:
                closed.append(trade)
        return closed
