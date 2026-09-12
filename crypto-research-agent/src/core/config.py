"""Загрузка конфигурации: секреты из .env, параметры из config.yaml.

Секреты никогда не попадают в config.yaml и никогда не логируются.
Денежные и процентные величины читаются как Decimal (в YAML заданы строками).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CONFIG_PATH = Path("config.yaml")


class Secrets(BaseSettings):
    """Секреты только из окружения/.env. В git не попадают."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


class ExchangeConfig(BaseModel):
    name: str = "bybit"
    market_type: str = "spot"
    timeout_sec: int = 20
    max_retries: int = 3
    retry_backoff_sec: Decimal = Decimal("1.0")


class MarketConfig(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ["BTC/USDT"])
    timeframe: str = "1h"
    candles_limit: int = 1000


class CostsConfig(BaseModel):
    """Издержки исполнения. Учитываются всегда: и в бэктесте, и в paper-режиме."""

    taker_fee_pct: Decimal = Decimal("0.055")
    slippage_pct: Decimal = Decimal("0.05")


class RiskConfig(BaseModel):
    initial_balance: Decimal = Decimal("10000")
    max_position_pct: Decimal = Decimal("2")
    max_open_positions: int = 3
    daily_loss_limit_pct: Decimal = Decimal("3")
    stop_loss_pct: Decimal = Decimal("1.5")
    take_profit_pct: Decimal = Decimal("3")


class StrategyConfig(BaseModel):
    name: str = "ema_cross"
    params: dict[str, int] = Field(default_factory=dict)


class NewsConfig(BaseModel):
    feeds: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    min_relevance: int = 1
    max_items: int = 40


class ResearchConfig(BaseModel):
    model: str = "claude-sonnet-4-5"
    max_tokens: int = 2000


class LoggingConfig(BaseModel):
    """Поле json из YAML; внутри зовётся json_output, чтобы не конфликтовать с pydantic."""

    model_config = ConfigDict(populate_by_name=True)

    level: str = "INFO"
    json_output: bool = Field(default=False, alias="json")


class DbConfig(BaseModel):
    path: str = "data/agent.db"


class AppConfig(BaseModel):
    """Полная конфигурация приложения."""

    exchange: ExchangeConfig = Field(default_factory=ExchangeConfig)
    market: MarketConfig = Field(default_factory=MarketConfig)
    costs: CostsConfig = Field(default_factory=CostsConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    news: NewsConfig = Field(default_factory=NewsConfig)
    research: ResearchConfig = Field(default_factory=ResearchConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    db: DbConfig = Field(default_factory=DbConfig)
    secrets: Secrets = Field(default_factory=Secrets)


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> AppConfig:
    """Читает config.yaml и .env, возвращает провалидированную конфигурацию."""
    config_path = Path(path)
    raw: dict = {}
    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            raw = loaded
    raw["secrets"] = Secrets()
    return AppConfig.model_validate(raw)
