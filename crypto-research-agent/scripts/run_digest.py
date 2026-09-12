"""Собрать RSS-новости, сохранить их и сформировать текстовый дайджест."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime

from src.core.config import load_config
from src.core.db import Database
from src.core.log import configure_logging, get_logger
from src.data.news import NewsClient
from src.research.agent import ResearchAgent


async def run(save_only: bool) -> str:
    """Загрузить новости, записать их в БД и при наличии ключа сделать дайджест."""

    config = load_config()
    configure_logging(config.logging.level)
    logger = get_logger()
    database = Database(config.project_root / config.storage.database_path)
    database.initialize()

    items = await NewsClient(config.news, config.exchange).fetch_all()
    database.save_news_items(
        (item.ts, item.source, item.url, item.title, item.summary, item.relevance)
        for item in items
    )
    logger.info("news_saved", items=len(items))
    if save_only or not config.secrets.anthropic_api_key:
        return f"Сохранено новостей: {len(items)}. Дайджест не запрашивался."

    prompt_path = config.project_root / "src" / "research" / "prompts" / "digest.md"
    agent = ResearchAgent(
        config.secrets.anthropic_api_key, config.exchange, prompt_path, config.research
    )
    digest = await agent.create_digest(items)
    today = datetime.now(tz=UTC).date().isoformat()
    database.save_digest(today, digest)
    logger.info("digest_saved", date=today)
    return digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--save-only", action="store_true", help="Только сохранить новости, без вызова Claude"
    )
    args = parser.parse_args()
    print(asyncio.run(run(args.save_only)))


if __name__ == "__main__":
    main()
