"""LLM-слой только для текстового анализа новостей."""

from __future__ import annotations

import asyncio
from pathlib import Path

from anthropic import Anthropic

from src.core.config import ExchangeConfig, ResearchConfig
from src.data.news import NewsItem


class ResearchAgent:
    """Создаёт дайджест; его результат никогда не передаётся стратегии."""

    def __init__(
        self,
        api_key: str,
        network: ExchangeConfig,
        prompt_path: Path,
        research: ResearchConfig,
    ) -> None:
        self.client = Anthropic(api_key=api_key, timeout=network.timeout_ms / 1000)
        self.network = network
        self.research = research
        self.prompt = prompt_path.read_text(encoding="utf-8")

    async def create_digest(self, items: list[NewsItem]) -> str:
        """Суммаризировать новости с ограниченным числом повторных попыток."""

        selected = items[: self.research.max_news_items]
        news_text = "\n".join(f"- {item.title}: {item.summary}" for item in selected)
        for attempt in range(self.network.max_retries):
            try:
                message = await asyncio.to_thread(
                    self.client.messages.create,
                    model=self.research.model,
                    max_tokens=self.research.max_tokens,
                    temperature=0,
                    system=self.prompt,
                    messages=[{"role": "user", "content": news_text}],
                )
                return "\n".join(
                    block.text for block in message.content if getattr(block, "type", "") == "text"
                )
            except Exception:
                if attempt + 1 >= self.network.max_retries:
                    raise
                await asyncio.sleep(float(self.network.retry_base_seconds * (2**attempt)))
        raise RuntimeError("Недостижимая ветка retry")

