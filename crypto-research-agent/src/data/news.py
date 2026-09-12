"""Новости: чтение RSS и фильтрация по ключевым словам.

LLM здесь не используется — фильтрация детерминированная.
"""

from __future__ import annotations

import time
from calendar import timegm
from dataclasses import dataclass

import feedparser
import httpx

from src.core.config import NewsConfig
from src.core.log import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class NewsItem:
    """Новость с оценкой релевантности."""

    ts: int
    source: str
    url: str
    title: str
    summary: str
    relevance: int


def relevance_score(text: str, keywords: list[str]) -> int:
    """Релевантность = число ключевых слов, встретившихся в тексте."""
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lowered)


def entry_timestamp_ms(entry: dict) -> int:
    """Время публикации в миллисекундах UTC; если его нет — текущее время."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed is None:
        return int(time.time() * 1000)
    return int(timegm(parsed) * 1000)


def fetch_feed(url: str, timeout_sec: int = 20, max_retries: int = 3) -> bytes:
    """Скачивает ленту с таймаутом и экспоненциальным backoff."""
    last_error: Exception | None = None
    for attempt in range(max(1, max_retries)):
        try:
            response = httpx.get(url, timeout=timeout_sec, follow_redirects=True)
            response.raise_for_status()
            return response.content
        except httpx.HTTPError as error:
            last_error = error
            delay = 1.0 * (2**attempt)
            log.warning("feed_error", url=url, attempt=attempt + 1, delay_sec=delay)
            time.sleep(delay)
    raise RuntimeError(f"не удалось прочитать ленту {url}: {last_error}")


def parse_feed(source: str, content: bytes, config: NewsConfig) -> list[NewsItem]:
    """Разбирает ленту и оставляет записи с релевантностью не ниже порога."""
    parsed = feedparser.parse(content)
    items: list[NewsItem] = []
    for entry in parsed.entries:
        title = str(entry.get("title", ""))
        summary = str(entry.get("summary", ""))
        url = str(entry.get("link", ""))
        if not url:
            continue
        score = relevance_score(f"{title} {summary}", config.keywords)
        if score < config.min_relevance:
            continue
        items.append(
            NewsItem(
                ts=entry_timestamp_ms(entry),
                source=source,
                url=url,
                title=title,
                summary=summary[:1000],
                relevance=score,
            )
        )
    items.sort(key=lambda item: (item.relevance, item.ts), reverse=True)
    return items[: config.max_items]


def collect_news(config: NewsConfig, timeout_sec: int = 20) -> list[NewsItem]:
    """Собирает новости со всех лент конфига. Ошибка одной ленты не ломает остальные."""
    collected: list[NewsItem] = []
    for feed_url in config.feeds:
        try:
            content = fetch_feed(feed_url, timeout_sec=timeout_sec)
        except RuntimeError as error:
            log.warning("feed_skipped", url=feed_url, error=str(error))
            continue
        collected.extend(parse_feed(feed_url, content, config))
    collected.sort(key=lambda item: (item.relevance, item.ts), reverse=True)
    return collected[: config.max_items]
