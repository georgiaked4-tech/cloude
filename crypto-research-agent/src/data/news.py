"""RSS-загрузчик новостей с таймаутами и ретраями."""

from __future__ import annotations

import asyncio
import calendar
import re
from dataclasses import dataclass
from functools import lru_cache

import feedparser
import httpx

from src.core.config import ExchangeConfig, NewsConfig


@lru_cache(maxsize=256)
def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    """Регулярное выражение для ключевого слова с границами слова."""

    return re.compile(rf"(?<!\w){re.escape(keyword)}(?!\w)", re.IGNORECASE)


@dataclass(frozen=True)
class NewsItem:
    ts: int
    source: str
    url: str
    title: str
    summary: str
    relevance: int = 0


class NewsClient:
    """Загружает RSS и не участвует в формировании торговых сигналов."""

    def __init__(self, news: NewsConfig, network: ExchangeConfig) -> None:
        self.news = news
        self.network = network

    async def _download(self, url: str) -> bytes:
        """Загрузить RSS с таймаутом, rate-limit обработкой и backoff."""

        timeout = httpx.Timeout(self.news.request_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            for attempt in range(self.network.max_retries):
                try:
                    response = await client.get(url)
                    if response.status_code == 429:
                        raise httpx.HTTPStatusError(
                            "Rate limit", request=response.request, response=response
                        )
                    response.raise_for_status()
                    return response.content
                except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError):
                    if attempt + 1 >= self.network.max_retries:
                        raise
                    await asyncio.sleep(float(self.network.retry_base_seconds * (2**attempt)))
        raise RuntimeError("Недостижимая ветка retry")

    def relevance(self, title: str, summary: str) -> int:
        """Релевантность = число ключевых слов конфига, встреченных в тексте.

        Совпадение идёт по границам слов, а не по подстроке: короткий тикер
        вроде "eth" иначе срабатывал бы на «whether» и «together» и протаскивал
        нерелевантные новости в платный запрос дайджеста. Оценка
        детерминированная и не обращается к LLM.
        """

        text = f"{title} {summary}"
        return sum(1 for keyword in self.news.keywords if _keyword_pattern(keyword).search(text))

    async def fetch_all(self) -> list[NewsItem]:
        """Загрузить ленты и оставить новости с релевантностью не ниже порога."""

        items: list[NewsItem] = []
        for url in self.news.feeds:
            parsed = feedparser.parse(await self._download(url))
            source = parsed.feed.get("title", url)
            for entry in parsed.entries:
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                ts = calendar.timegm(published) * 1000 if published else 0
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                score = self.relevance(title, summary)
                if score < self.news.min_relevance:
                    continue
                items.append(
                    NewsItem(
                        ts=ts,
                        source=source,
                        url=entry.get("link", ""),
                        title=title,
                        summary=summary,
                        relevance=score,
                    )
                )
        items.sort(key=lambda item: (-item.relevance, -item.ts))
        return items

