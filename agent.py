#!/usr/bin/env python3
"""
Агент мониторинга финансовых рынков с отправкой дайджеста в Telegram-канал.

Запуск:
    python agent.py          — бесконечный цикл (утренний + вечерний дайджест + алерты)
    python agent.py --once   — разовая отправка дайджеста
"""

import argparse
import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import aiohttp
import feedparser

from config import (
    COINGECKO_API_URL,
    EVENING_DIGEST_HOUR,
    HTTP_TIMEOUT,
    MAX_NEWS_PER_DIGEST,
    MORNING_DIGEST_HOUR,
    PRICE_ALERT_THRESHOLD,
    PRICE_CHECK_INTERVAL,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from sources import KEYWORDS, RSS_FEEDS, TRACKED_COINS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fin-agent")

# ── Модели данных ──────────────────────────────────────────


@dataclass
class NewsItem:
    """Одна новость."""
    title: str
    link: str
    source: str
    published: str
    score: int = 0


@dataclass
class PriceSnapshot:
    """Снимок цен криптовалют."""
    prices: dict[str, float] = field(default_factory=dict)       # coin_id -> usd
    changes_24h: dict[str, float] = field(default_factory=dict)  # coin_id -> %


# ── NewsCollector ──────────────────────────────────────────


class NewsCollector:
    """Асинхронный сбор и скоринг новостей из RSS-фидов."""

    def __init__(self) -> None:
        self._keywords = [kw.lower() for kw in KEYWORDS]

    async def collect(self) -> list[NewsItem]:
        """Собрать новости из всех источников параллельно."""
        timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = [self._fetch_feed(session, feed) for feed in RSS_FEEDS]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        all_news: list[NewsItem] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Ошибка загрузки фида: %s", result)
                continue
            all_news.extend(result)

        # Скоринг и сортировка
        for item in all_news:
            item.score = self._score(item.title)
        all_news.sort(key=lambda n: n.score, reverse=True)
        return all_news[:MAX_NEWS_PER_DIGEST]

    async def _fetch_feed(
        self, session: aiohttp.ClientSession, feed: dict[str, str]
    ) -> list[NewsItem]:
        """Загрузить и распарсить один RSS-фид."""
        try:
            async with session.get(feed["url"]) as resp:
                body = await resp.text()
        except Exception as exc:
            logger.warning("Не удалось загрузить %s: %s", feed["name"], exc)
            return []

        parsed = feedparser.parse(body)
        items: list[NewsItem] = []
        for entry in parsed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "")
            published = entry.get("published", "")
            if title:
                items.append(
                    NewsItem(
                        title=title,
                        link=link,
                        source=feed["name"],
                        published=published,
                    )
                )
        logger.info("Загружено %d новостей из %s", len(items), feed["name"])
        return items

    def _score(self, text: str) -> int:
        """Подсчитать релевантность заголовка по ключевым словам."""
        lower = text.lower()
        return sum(1 for kw in self._keywords if kw in lower)


# ── PriceFetcher ───────────────────────────────────────────


class PriceFetcher:
    """Получение цен криптовалют через бесплатный CoinGecko API."""

    async def fetch(self) -> PriceSnapshot:
        """Получить текущие цены и суточное изменение."""
        ids = ",".join(TRACKED_COINS.keys())
        url = (
            f"{COINGECKO_API_URL}/simple/price"
            f"?ids={ids}&vs_currencies=usd&include_24hr_change=true"
        )
        snapshot = PriceSnapshot()
        timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    data = await resp.json()
            for coin_id in TRACKED_COINS:
                info = data.get(coin_id, {})
                snapshot.prices[coin_id] = info.get("usd", 0.0)
                snapshot.changes_24h[coin_id] = info.get("usd_24h_change", 0.0)
        except Exception as exc:
            logger.warning("Ошибка получения цен: %s", exc)
        return snapshot


# ── Formatter ──────────────────────────────────────────────


class Formatter:
    """Форматирование дайджеста в Telegram MarkdownV2."""

    # Символы, которые нужно экранировать в MarkdownV2
    _ESCAPE_RE = re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])")

    @classmethod
    def escape(cls, text: str) -> str:
        """Экранирование спецсимволов для MarkdownV2."""
        return cls._ESCAPE_RE.sub(r"\\\1", text)

    @classmethod
    def format_digest(
        cls, news: list[NewsItem], snapshot: PriceSnapshot
    ) -> str:
        """Сформировать полный текст дайджеста."""
        now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
        lines: list[str] = []

        # Заголовок
        lines.append(f"*{cls.escape('📊 Финансовый дайджест')}*")
        lines.append(f"_{cls.escape(now)}_")
        lines.append("")

        # Цены
        if snapshot.prices:
            lines.append(f"*{cls.escape('💰 Криптовалюты')}*")
            for coin_id, ticker in TRACKED_COINS.items():
                price = snapshot.prices.get(coin_id, 0)
                change = snapshot.changes_24h.get(coin_id, 0)
                arrow = "🟢" if change >= 0 else "🔴"
                price_str = f"${price:,.2f}"
                change_str = f"{change:+.2f}%"
                lines.append(
                    f"  {arrow} *{cls.escape(ticker)}*: "
                    f"{cls.escape(price_str)} "
                    f"\\({cls.escape(change_str)}\\)"
                )
            lines.append("")

        # Новости
        if news:
            lines.append(f"*{cls.escape('📰 Топ-новости')}*")
            for i, item in enumerate(news, 1):
                title_esc = cls.escape(item.title)
                source_esc = cls.escape(item.source)
                # Ссылка в формате MarkdownV2: [текст](url)
                link_esc = cls.escape(item.link)
                lines.append(
                    f"{cls.escape(str(i) + '.')} [{title_esc}]({link_esc})"
                    f"\n    _{source_esc}_"
                )
            lines.append("")

        lines.append(f"_{cls.escape('— Финансовый агент 🤖')}_")
        return "\n".join(lines)

    @classmethod
    def format_price_alert(
        cls, coin_id: str, ticker: str, price: float, change: float
    ) -> str:
        """Сформировать сообщение ценового алерта."""
        arrow = "🟢📈" if change >= 0 else "🔴📉"
        price_str = f"${price:,.2f}"
        change_str = f"{change:+.2f}%"
        return (
            f"*{cls.escape('⚠️ ЦЕНОВОЙ АЛЕРТ')}*\n\n"
            f"{arrow} *{cls.escape(ticker)}*: {cls.escape(price_str)}\n"
            f"Изменение за 24ч: *{cls.escape(change_str)}*"
        )


# ── TelegramChannel ───────────────────────────────────────


class TelegramChannel:
    """Отправка сообщений в Telegram-канал через Bot API."""

    MAX_MESSAGE_LEN = 4096

    def __init__(self, token: str, chat_id: str) -> None:
        self._token = token
        self._chat_id = chat_id
        self._api = f"https://api.telegram.org/bot{token}"

    async def send(self, text: str, parse_mode: str = "MarkdownV2") -> None:
        """
        Отправить сообщение в канал.
        Если текст длиннее 4096 символов — разбить на части (chunked).
        """
        chunks = self._split(text)
        timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for chunk in chunks:
                payload = {
                    "chat_id": self._chat_id,
                    "text": chunk,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                }
                async with session.post(
                    f"{self._api}/sendMessage", json=payload
                ) as resp:
                    result = await resp.json()
                    if not result.get("ok"):
                        logger.error(
                            "Ошибка отправки в Telegram: %s",
                            result.get("description", "unknown"),
                        )
                    else:
                        logger.info("Сообщение отправлено в канал")

    def _split(self, text: str) -> list[str]:
        """Разбить длинный текст на части по границам строк."""
        if len(text) <= self.MAX_MESSAGE_LEN:
            return [text]
        chunks: list[str] = []
        while text:
            if len(text) <= self.MAX_MESSAGE_LEN:
                chunks.append(text)
                break
            # Ищем последний перенос строки в пределах лимита
            cut = text.rfind("\n", 0, self.MAX_MESSAGE_LEN)
            if cut == -1:
                cut = self.MAX_MESSAGE_LEN
            chunks.append(text[:cut])
            text = text[cut:].lstrip("\n")
        return chunks


# ── FinNewsAgent (оркестратор) ─────────────────────────────


class FinNewsAgent:
    """
    Главный оркестратор:
    - утренний и вечерний дайджест по расписанию
    - алерты при резком изменении цены
    """

    def __init__(self) -> None:
        self.collector = NewsCollector()
        self.price_fetcher = PriceFetcher()
        self.formatter = Formatter()
        self.channel = TelegramChannel(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        self._last_digest_hour: int | None = None
        self._prev_prices: dict[str, float] = {}

    async def send_digest(self) -> None:
        """Собрать и отправить один дайджест."""
        logger.info("Сбор дайджеста...")
        news, snapshot = await asyncio.gather(
            self.collector.collect(),
            self.price_fetcher.fetch(),
        )
        text = self.formatter.format_digest(news, snapshot)
        await self.channel.send(text)
        # Сохраняем цены для будущих алертов
        self._prev_prices = dict(snapshot.prices)
        logger.info("Дайджест отправлен (%d новостей)", len(news))

    async def check_alerts(self) -> None:
        """Проверить цены и отправить алерт при сильном отклонении."""
        snapshot = await self.price_fetcher.fetch()
        for coin_id, ticker in TRACKED_COINS.items():
            current = snapshot.prices.get(coin_id, 0)
            prev = self._prev_prices.get(coin_id)
            if not prev or not current:
                continue
            change_pct = ((current - prev) / prev) * 100
            if abs(change_pct) >= PRICE_ALERT_THRESHOLD:
                text = self.formatter.format_price_alert(
                    coin_id, ticker, current, change_pct
                )
                await self.channel.send(text)
                logger.info(
                    "Алерт отправлен: %s %.2f%%", ticker, change_pct
                )
                # Обновляем базовую цену после алерта
                self._prev_prices[coin_id] = current

    async def run_loop(self) -> None:
        """Бесконечный цикл: дайджесты по расписанию + алерты."""
        logger.info("Агент запущен в режиме цикла")

        # Начальный сбор цен
        snapshot = await self.price_fetcher.fetch()
        self._prev_prices = dict(snapshot.prices)

        while True:
            now = datetime.now(timezone.utc)
            hour = now.hour

            # Отправляем дайджест, если подошёл час и ещё не отправляли
            if hour in (MORNING_DIGEST_HOUR, EVENING_DIGEST_HOUR):
                if self._last_digest_hour != hour:
                    await self.send_digest()
                    self._last_digest_hour = hour

            # Проверяем алерты
            await self.check_alerts()

            # Ждём до следующей проверки
            await asyncio.sleep(PRICE_CHECK_INTERVAL)


# ── Точка входа ───────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Агент мониторинга финансовых рынков"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Отправить один дайджест и выйти",
    )
    args = parser.parse_args()

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error(
            "Задайте TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID "
            "(переменные окружения или config.py)"
        )
        raise SystemExit(1)

    agent = FinNewsAgent()

    if args.once:
        asyncio.run(agent.send_digest())
    else:
        asyncio.run(agent.run_loop())


if __name__ == "__main__":
    main()
