"""Загрузка настроек из YAML и секретов из окружения."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.timeframe import timeframe_minutes


class Secrets(BaseSettings):
    """Секреты проекта, которые никогда не попадают в YAML."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = Field(default=None, alias="TELEGRAM_CHAT_ID")


class ExchangeConfig(BaseModel):
    name: str = "bybit"
    timeout_ms: int = 10_000
    max_retries: int = 3
    retry_base_seconds: Decimal = Decimal("0.5")

    @field_validator("max_retries")
    @classmethod
    def validate_retries(cls, value: int) -> int:
        if not 1 <= value <= 3:
            raise ValueError("max_retries должен быть от 1 до 3")
        return value


class TradingConfig(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ["BTC/USDT"])
    timeframe: str = "1h"
    initial_balance: Decimal = Decimal("10000")
    taker_fee_pct: Decimal = Decimal("0.055")
    slippage_pct: Decimal = Decimal("0.05")

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, value: str) -> str:
        timeframe_minutes(value)
        return value

    @field_validator("initial_balance")
    @classmethod
    def validate_balance(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("initial_balance должен быть положительным")
        return value

    @field_validator("taker_fee_pct", "slippage_pct")
    @classmethod
    def validate_costs(cls, value: Decimal) -> Decimal:
        # Отрицательная комиссия или проскальзывание улучшали бы цену сделки и
        # рисовали бы прибыль там, где её нет, поэтому опечатка в знаке ловится
        # на загрузке конфига.
        if value < 0:
            raise ValueError("Комиссия и проскальзывание не могут быть отрицательными")
        return value


class StrategyConfig(BaseModel):
    fast_ema: int = 12
    slow_ema: int = 26

    @field_validator("slow_ema")
    @classmethod
    def validate_slow_ema(cls, value: int, info: Any) -> int:
        fast = info.data.get("fast_ema", 12)
        if value <= fast:
            raise ValueError("slow_ema должен быть больше fast_ema")
        return value


class RiskConfig(BaseModel):
    max_position_pct: Decimal = Decimal("2")
    max_open_positions: int = 3
    daily_loss_limit_pct: Decimal = Decimal("3")
    stop_loss_pct: Decimal = Decimal("2")
    take_profit_pct: Decimal = Decimal("4")

    @field_validator(
        "max_position_pct", "daily_loss_limit_pct", "stop_loss_pct", "take_profit_pct"
    )
    @classmethod
    def validate_percentages(cls, value: Decimal) -> Decimal:
        # Стоп обязателен для каждой позиции, поэтому нулевой или отрицательный
        # процент риска недопустим; доля больше 100% тоже лишена смысла.
        if not 0 < value <= 100:
            raise ValueError("Процент риска должен быть в диапазоне (0, 100]")
        return value

    @field_validator("max_open_positions")
    @classmethod
    def validate_max_open_positions(cls, value: int) -> int:
        if value < 1:
            raise ValueError("max_open_positions должен быть не меньше 1")
        return value


class StorageConfig(BaseModel):
    database_path: str = "data/agent.db"


class LoggingConfig(BaseModel):
    level: str = "INFO"


class NewsConfig(BaseModel):
    feeds: list[str] = Field(default_factory=list)
    request_timeout_seconds: int = 10
    keywords: list[str] = Field(default_factory=list)
    min_relevance: int = 1


class ResearchConfig(BaseModel):
    """Параметры текстового research-слоя; на сигналы стратегии не влияют."""

    model: str = "claude-sonnet-5"
    max_tokens: int = 1200
    max_news_items: int = 50


class AppConfig(BaseModel):
    exchange: ExchangeConfig
    trading: TradingConfig
    strategy: StrategyConfig
    risk: RiskConfig
    storage: StorageConfig
    logging: LoggingConfig
    news: NewsConfig
    research: ResearchConfig = Field(default_factory=ResearchConfig)
    secrets: Secrets
    project_root: Path


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    """Загрузить публичные настройки и добавить секреты из `.env`."""

    config_path = Path(path).resolve()
    with config_path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}
    raw["secrets"] = Secrets()
    raw["project_root"] = config_path.parent
    return AppConfig.model_validate(raw)

