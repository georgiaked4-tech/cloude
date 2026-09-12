"""Тесты загрузки конфигурации."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from src.core.config import load_config
from src.core.log import mask_secrets


def test_config_yaml_loads_decimals() -> None:
    """Денежные величины из config.yaml читаются как Decimal."""
    config = load_config(Path(__file__).resolve().parents[1] / "config.yaml")
    assert config.costs.taker_fee_pct == Decimal("0.055")
    assert config.costs.slippage_pct == Decimal("0.05")
    assert isinstance(config.risk.max_position_pct, Decimal)
    assert config.exchange.name == "bybit"


def test_secrets_are_masked_in_logs() -> None:
    """Секреты в логах заменяются маской."""
    event = mask_secrets(None, "info", {"anthropic_api_key": "sk-ant-secret", "symbol": "BTC/USDT"})
    assert event["anthropic_api_key"] == "***"
    assert event["symbol"] == "BTC/USDT"
