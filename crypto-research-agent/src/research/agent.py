"""Research-слой: обращения к Claude API.

Важно: LLM участвует только в текстовом research-слое (новости, регуляторика, дайджесты).
Торговые сигналы формирует детерминированный код стратегии, сюда они не попадают.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import anthropic

from src.core.config import AppConfig
from src.core.log import get_logger
from src.data.news import NewsItem

log = get_logger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "digest.md"


def format_news_block(items: list[NewsItem]) -> str:
    """Готовит список новостей для вставки в промпт."""
    lines = []
    for item in items:
        moment = datetime.fromtimestamp(item.ts / 1000, tz=UTC)
        published = moment.strftime("%Y-%m-%d %H:%M")
        lines.append(f"- [{published} UTC] {item.title} ({item.url})")
    return "\n".join(lines) if lines else "- новостей за период нет"


def build_digest_prompt(items: list[NewsItem]) -> str:
    """Подставляет новости в шаблон промпта."""
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("{news_block}", format_news_block(items))


class ResearchAgent:
    """Тонкая обёртка над Claude API для текстовых задач."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        if not config.secrets.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY не задан в .env")
        self.client = anthropic.Anthropic(api_key=config.secrets.anthropic_api_key)

    def make_digest(self, items: list[NewsItem]) -> str:
        """Возвращает текст дайджеста. На торговые решения не влияет."""
        prompt = build_digest_prompt(items)
        response = self.client.messages.create(
            model=self.config.research.model,
            max_tokens=self.config.research.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [block.text for block in response.content if getattr(block, "type", "") == "text"]
        digest = "\n".join(parts).strip()
        log.info("digest_created", items=len(items), length=len(digest))
        return digest
