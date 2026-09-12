from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.core.config import RiskConfig, TradingConfig


@pytest.mark.parametrize("field", ["taker_fee_pct", "slippage_pct"])
def test_negative_costs_are_rejected(field: str) -> None:
    # Отрицательная комиссия кредитовала бы счёт и рисовала прибыльный бэктест.
    with pytest.raises(ValidationError):
        TradingConfig(**{field: "-0.05"})


def test_non_positive_balance_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TradingConfig(initial_balance="0")


def test_unsupported_timeframe_is_rejected_at_load() -> None:
    with pytest.raises(ValidationError):
        TradingConfig(timeframe="1M")


@pytest.mark.parametrize(
    "field", ["max_position_pct", "daily_loss_limit_pct", "stop_loss_pct", "take_profit_pct"]
)
def test_risk_percentages_must_be_within_bounds(field: str) -> None:
    with pytest.raises(ValidationError):
        RiskConfig(**{field: "0"})
    with pytest.raises(ValidationError):
        RiskConfig(**{field: "101"})


def test_valid_configuration_is_accepted() -> None:
    trading = TradingConfig(taker_fee_pct="0.055", slippage_pct="0", timeframe="15m")
    assert trading.slippage_pct == Decimal("0")
    assert RiskConfig(max_open_positions=1).max_open_positions == 1
    with pytest.raises(ValidationError):
        RiskConfig(max_open_positions=0)
