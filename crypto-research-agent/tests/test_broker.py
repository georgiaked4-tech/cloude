"""Тесты симулятора исполнения: издержки, стоп, тейк, лимиты."""

from __future__ import annotations

from decimal import Decimal

from src.core.config import CostsConfig, RiskConfig
from src.paper.broker import EXIT_STOP_LOSS, EXIT_TAKE_PROFIT, PaperBroker
from src.risk.limits import RiskManager
from src.strategy.base import SIDE_BUY, SIDE_SELL, Candle, Signal

TS = 1_700_000_000_000


def make_broker(risk_config: RiskConfig, costs_config: CostsConfig) -> PaperBroker:
    """Брокер с балансом из конфигурации риска."""
    return PaperBroker(risk_config.initial_balance, costs_config, RiskManager(risk_config))


def buy_signal(price: str = "100") -> Signal:
    """Сигнал на покупку BTC/USDT."""
    return Signal(ts=TS, symbol="BTC/USDT", side=SIDE_BUY, price=Decimal(price), reason="тест")


def candle(low: str, high: str, close: str, ts: int = TS + 1000) -> Candle:
    """Свеча с заданными границами."""
    return Candle(
        ts=ts,
        open=Decimal(close),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("1"),
    )


def test_entry_applies_slippage_and_fee(
    risk_config: RiskConfig, costs_config: CostsConfig
) -> None:
    """Вход дороже рынка на проскальзывание, комиссия списывается с баланса."""
    broker = make_broker(risk_config, costs_config)
    position = broker.try_open(buy_signal("100"))
    assert position is not None
    # 100 * (1 + 0.05/100) = 100.05
    assert position.entry_price == Decimal("100.05")
    expected_fee = position.qty * position.entry_price * Decimal("0.055") / Decimal("100")
    assert position.entry_fee == expected_fee
    assert broker.balance == Decimal("10000") - position.qty * position.entry_price - expected_fee


def test_stop_loss_closes_position(risk_config: RiskConfig, costs_config: CostsConfig) -> None:
    """Пробой стопа закрывает позицию с убытком."""
    broker = make_broker(risk_config, costs_config)
    position = broker.try_open(buy_signal("100"))
    assert position is not None
    trade = broker.on_candle("BTC/USDT", candle(low="90", high="101", close="95"))
    assert trade is not None
    assert trade.exit_reason == EXIT_STOP_LOSS
    assert trade.pnl < 0
    assert broker.open_positions == 0


def test_take_profit_closes_position(risk_config: RiskConfig, costs_config: CostsConfig) -> None:
    """Достижение тейка закрывает позицию с прибылью после комиссий."""
    broker = make_broker(risk_config, costs_config)
    position = broker.try_open(buy_signal("100"))
    assert position is not None
    trade = broker.on_candle("BTC/USDT", candle(low="100", high="110", close="105"))
    assert trade is not None
    assert trade.exit_reason == EXIT_TAKE_PROFIT
    assert trade.pnl > 0
    assert trade.gross_pnl > trade.pnl  # комиссии уменьшают результат


def test_stop_wins_when_both_levels_touched(
    risk_config: RiskConfig, costs_config: CostsConfig
) -> None:
    """Если в одной свече задеты стоп и тейк, консервативно считаем стоп."""
    broker = make_broker(risk_config, costs_config)
    broker.try_open(buy_signal("100"))
    trade = broker.on_candle("BTC/USDT", candle(low="90", high="110", close="105"))
    assert trade is not None
    assert trade.exit_reason == EXIT_STOP_LOSS


def test_fees_always_charged(risk_config: RiskConfig, costs_config: CostsConfig) -> None:
    """Комиссия сделки — сумма комиссий входа и выхода, всегда больше нуля."""
    broker = make_broker(risk_config, costs_config)
    broker.try_open(buy_signal("100"))
    trade = broker.close("BTC/USDT", TS + 1000, Decimal("100"), "signal")
    assert trade is not None
    assert trade.fee > 0
    assert trade.pnl < trade.gross_pnl


def test_max_open_positions_enforced_by_broker(
    risk_config: RiskConfig, costs_config: CostsConfig
) -> None:
    """Брокер не открывает больше позиций, чем разрешает риск-модуль."""
    broker = make_broker(risk_config, costs_config)
    for symbol in ("BTC/USDT", "ETH/USDT", "SOL/USDT"):
        signal = Signal(ts=TS, symbol=symbol, side=SIDE_BUY, price=Decimal("100"), reason="тест")
        assert broker.try_open(signal) is not None
    extra = Signal(ts=TS, symbol="XRP/USDT", side=SIDE_BUY, price=Decimal("100"), reason="тест")
    assert broker.try_open(extra) is None
    assert broker.open_positions == 3


def test_no_duplicate_position_for_same_symbol(
    risk_config: RiskConfig, costs_config: CostsConfig
) -> None:
    """Повторный вход по тому же символу игнорируется."""
    broker = make_broker(risk_config, costs_config)
    assert broker.try_open(buy_signal("100")) is not None
    assert broker.try_open(buy_signal("101")) is None


def test_sell_signal_does_not_open_position(
    risk_config: RiskConfig, costs_config: CostsConfig
) -> None:
    """Шортов нет: сигнал на продажу позицию не открывает."""
    broker = make_broker(risk_config, costs_config)
    signal = Signal(ts=TS, symbol="BTC/USDT", side=SIDE_SELL, price=Decimal("100"), reason="тест")
    assert broker.try_open(signal) is None


def test_daily_loss_limit_stops_new_entries(costs_config: CostsConfig) -> None:
    """После убытка сверх дневного лимита брокер перестаёт открывать позиции."""
    config = RiskConfig(
        initial_balance=Decimal("10000"),
        max_position_pct=Decimal("50"),
        max_open_positions=3,
        daily_loss_limit_pct=Decimal("0.1"),
        stop_loss_pct=Decimal("1.5"),
        take_profit_pct=Decimal("3"),
    )
    broker = make_broker(config, costs_config)
    broker.try_open(buy_signal("100"))
    trade = broker.on_candle("BTC/USDT", candle(low="90", high="95", close="92"))
    assert trade is not None and trade.pnl < 0
    assert broker.risk.blocked is True
    assert broker.try_open(buy_signal("100")) is None


def test_equity_counts_open_positions(
    risk_config: RiskConfig, costs_config: CostsConfig
) -> None:
    """Капитал = свободный баланс + оценка открытых позиций."""
    broker = make_broker(risk_config, costs_config)
    position = broker.try_open(buy_signal("100"))
    assert position is not None
    prices = {"BTC/USDT": Decimal("100.05")}
    assert broker.equity(prices) == broker.balance + position.qty * Decimal("100.05")


def test_close_all_closes_every_position(
    risk_config: RiskConfig, costs_config: CostsConfig
) -> None:
    """close_all закрывает все позиции в конце прогона."""
    broker = make_broker(risk_config, costs_config)
    broker.try_open(buy_signal("100"))
    eth = Signal(ts=TS, symbol="ETH/USDT", side=SIDE_BUY, price=Decimal("50"), reason="тест")
    broker.try_open(eth)
    closed = broker.close_all(TS + 2000, {"BTC/USDT": Decimal("100"), "ETH/USDT": Decimal("50")})
    assert len(closed) == 2
    assert broker.open_positions == 0
