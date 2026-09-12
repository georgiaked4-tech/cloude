from decimal import Decimal

from src.core.config import RiskConfig, TradingConfig
from src.paper.broker import PaperBroker
from src.risk.limits import RiskManager
from src.strategy.base import Signal


def make_broker() -> PaperBroker:
    trading = TradingConfig(
        initial_balance="10000", taker_fee_pct="0.055", slippage_pct="0.05"
    )
    risk = RiskManager(
        RiskConfig(
            max_position_pct="2",
            max_open_positions=3,
            daily_loss_limit_pct="3",
            stop_loss_pct="2",
            take_profit_pct="4",
        )
    )
    return PaperBroker(trading, risk)


def buy_signal(price: str = "100") -> Signal:
    return Signal(1, "BTC/USDT", "test", "buy", Decimal(price), "test")


def test_open_uses_decimal_slippage_fee_and_position_limit() -> None:
    broker = make_broker()
    opened, _ = broker.open_long(1, buy_signal())
    position = broker.positions["BTC/USDT"]
    assert opened is True
    assert position.entry_price == Decimal("100.05")
    assert position.entry_fee == Decimal("0.11")
    assert position.entry_price * position.qty == Decimal("200")


def test_stop_loss_closes_position_and_counts_both_fees() -> None:
    broker = make_broker()
    broker.open_long(1, buy_signal())
    position = broker.positions["BTC/USDT"]
    trade = broker.process_price("BTC/USDT", position.stop_price, position.stop_price, 2)
    assert trade is not None
    assert trade.exit_reason == "stop_loss"
    assert trade.fee > Decimal("0.11")
    assert trade.pnl < 0


def test_take_profit_closes_position() -> None:
    broker = make_broker()
    broker.open_long(1, buy_signal())
    position = broker.positions["BTC/USDT"]
    trade = broker.process_price("BTC/USDT", position.take_price, position.take_price, 2)
    assert trade is not None
    assert trade.exit_reason == "take_profit"
    assert trade.pnl > 0


def test_sell_signal_cannot_open_a_short() -> None:
    broker = make_broker()
    signal = Signal(1, "BTC/USDT", "test", "sell", Decimal("100"), "test")
    opened, _ = broker.open_long(1, signal)
    assert opened is False
    assert broker.positions == {}



def test_restored_position_gets_the_same_stop_and_take() -> None:
    broker = make_broker()
    broker.open_long(1, buy_signal())
    original = broker.positions.pop("BTC/USDT")
    restored = broker.restore_position(
        original.signal_id, original.symbol, original.qty, original.entry_price,
        original.entry_ts, original.entry_fee,
    )
    assert restored.stop_price == original.stop_price
    assert restored.take_price == original.take_price
    assert broker.positions["BTC/USDT"] == restored


def test_equity_includes_open_position_value() -> None:
    broker = make_broker()
    broker.open_long(1, buy_signal())
    position = broker.positions["BTC/USDT"]
    assert broker.equity({"BTC/USDT": position.entry_price}) == broker.balance + Decimal("200")
    assert broker.equity({}) == broker.balance


def test_day_reset_uses_marked_equity_not_free_balance() -> None:
    broker = make_broker()
    broker.open_long(1, buy_signal())
    position = broker.positions["BTC/USDT"]
    marked = broker.equity({"BTC/USDT": position.entry_price})
    broker.reset_utc_day(marked)
    # База дневного лимита должна включать деньги, запертые в позиции.
    assert broker.day_start_balance == marked
    assert broker.day_start_balance > broker.balance
    assert broker.daily_pnl == Decimal(0)


def test_set_state_restores_daily_counters() -> None:
    broker = make_broker()
    broker.set_state(Decimal("9500"), Decimal("10000"), Decimal("-500"))
    assert broker.balance == Decimal("9500")
    decision = broker.risk.check_open(
        broker.day_start_balance, broker.daily_pnl, len(broker.positions)
    )
    # Убыток 500 при лимите 3% от 10000 = 300 — новые входы запрещены.
    assert decision.allowed is False
