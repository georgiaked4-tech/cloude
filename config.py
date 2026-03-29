"""
Конфигурация агента мониторинга финансовых рынков.

Перед запуском задайте переменные окружения:
  TELEGRAM_BOT_TOKEN  — токен бота из @BotFather
  TELEGRAM_CHAT_ID    — ID канала (например, @my_channel или -100...)
"""

import os

# ── Telegram ────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Расписание дайджестов (часы UTC) ────────────────────────
MORNING_DIGEST_HOUR: int = 6   # утренний дайджест
EVENING_DIGEST_HOUR: int = 18  # вечерний дайджест

# ── Интервал проверки цен для алертов (секунды) ─────────────
PRICE_CHECK_INTERVAL: int = 300  # каждые 5 минут

# ── Порог алерта: изменение цены в % ────────────────────────
PRICE_ALERT_THRESHOLD: float = 5.0  # алерт при изменении >= 5%

# ── Максимум новостей в одном дайджесте ─────────────────────
MAX_NEWS_PER_DIGEST: int = 15

# ── Таймаут HTTP-запросов (секунды) ─────────────────────────
HTTP_TIMEOUT: int = 15

# ── CoinGecko API (бесплатный, без ключа) ──────────────────
COINGECKO_API_URL: str = "https://api.coingecko.com/api/v3"
