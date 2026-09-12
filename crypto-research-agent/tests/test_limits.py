from decimal import Decimal

from src.core.config import RiskConfig
from src.risk.limits import RiskManager


def make_manager() -> RiskManager:
    return RiskManager(
        RiskConfig(
            max_position_pct="2",
            max_open_positions=3,
            daily_loss_limit_pct="3",
            stop_loss_pct="2",
            take_profit_pct="4",
        )
    )


def test_position_size_is_limited_to_configured_percent() -> None:
    manager = make_manager()
    assert manager.position_notional(Decimal("10000")) == Decimal("200")


def test_open_position_count_limit() -> None:
    decision = make_manager().check_open(Decimal("10000"), Decimal("0"), 3)
    assert decision.allowed is False


def test_daily_loss_limit() -> None:
    decision = make_manager().check_open(Decimal("10000"), Decimal("-300"), 0)
    assert decision.allowed is False


def test_stop_and_take_are_mandatory_and_deterministic() -> None:
    stop, take = make_manager().exit_prices(Decimal("100"))
    assert stop == Decimal("98")
    assert take == Decimal("104")



def test_utc_day_start_is_midnight_utc() -> None:
    from src.risk.limits import utc_day_start_ms

    # 2023-11-14 22:13:20 UTC → 2023-11-14 00:00:00 UTC.
    assert utc_day_start_ms(1_700_000_000_000) == 1_699_920_000_000
    assert utc_day_start_ms(1_699_920_000_000) == 1_699_920_000_000
