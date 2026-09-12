"""Общие фикстуры тестов."""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.core.config import CostsConfig, RiskConfig

DAY_MS = 24 * 60 * 60 * 1000


@pytest.fixture
def risk_config() -> RiskConfig:
    """Базовая конфигурация риска для тестов."""
    return RiskConfig(
        initial_balance=Decimal("10000"),
        max_position_pct=Decimal("2"),
        max_open_positions=3,
        daily_loss_limit_pct=Decimal("3"),
        stop_loss_pct=Decimal("1.5"),
        take_profit_pct=Decimal("3"),
    )


@pytest.fixture
def costs_config() -> CostsConfig:
    """Комиссия и проскальзывание из правил проекта."""
    return CostsConfig(taker_fee_pct=Decimal("0.055"), slippage_pct=Decimal("0.05"))
