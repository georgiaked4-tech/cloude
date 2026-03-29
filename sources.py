"""
RSS-источники и ключевые слова для фильтрации новостей.
"""

# ── RSS-фиды ───────────────────────────────────────────────
RSS_FEEDS: list[dict[str, str]] = [
    # Российские источники
    {
        "name": "РБК",
        "url": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
        "lang": "ru",
    },
    {
        "name": "Smart-Lab",
        "url": "https://smart-lab.ru/rss/",
        "lang": "ru",
    },
    {
        "name": "Финам",
        "url": "https://www.finam.ru/analysis/conews/rsspoint/",
        "lang": "ru",
    },
    # Международные источники
    {
        "name": "CoinDesk",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "lang": "en",
    },
    {
        "name": "CoinTelegraph",
        "url": "https://cointelegraph.com/rss",
        "lang": "en",
    },
    {
        "name": "Yahoo Finance",
        "url": "https://finance.yahoo.com/news/rssindex",
        "lang": "en",
    },
    {
        "name": "MarketWatch",
        "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "lang": "en",
    },
    {
        "name": "Investing.com",
        "url": "https://www.investing.com/rss/news.rss",
        "lang": "en",
    },
]

# ── Ключевые слова для скоринга (чем больше совпадений, тем выше приоритет)
# Все слова приведены в нижнем регистре для сравнения
KEYWORDS: list[str] = [
    # Криптовалюты
    "btc", "bitcoin", "биткоин", "биткойн",
    "eth", "ethereum", "эфир", "эфириум",
    "crypto", "крипто", "криптовалют",
    # Фондовый рынок
    "s&p", "s&p 500", "nasdaq", "dow jones",
    "мосбиржа", "moex", "ртс", "rts",
    # Сырьё
    "нефть", "oil", "brent", "wti",
    "золото", "gold",
    "газ", "gas",
    # Валюты
    "рубль", "рубл", "usd/rub", "eur/rub",
    "доллар", "евро", "юань",
    # Регуляторы и макро
    "фрс", "fed", "цб", "центробанк", "ставк",
    "инфляци", "inflation",
    "ввп", "gdp",
    "санкци", "sanctions",
    # Общие финансовые
    "ipo", "дивиденд", "dividend",
    "обвал", "crash", "rally", "ралли",
    "дефолт", "default",
]

# ── Криптовалюты для отслеживания цен через CoinGecko ──────
TRACKED_COINS: dict[str, str] = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
}
