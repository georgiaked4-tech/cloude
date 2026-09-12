"""Telegram-бот: только отправка сообщений и команды /status, /report, /stop.

Управление позициями через бота невозможно: реальной торговли в проекте нет.
Токен берётся из .env и никогда не попадает в сообщения и логи.
"""

from __future__ import annotations

from collections.abc import Callable

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from src.core.config import AppConfig
from src.core.log import get_logger

log = get_logger(__name__)


class TelegramNotifier:
    """Отправка уведомлений и три read-only команды."""

    def __init__(
        self,
        config: AppConfig,
        status_provider: Callable[[], str],
        report_provider: Callable[[], str],
        stop_handler: Callable[[], str],
    ) -> None:
        if not config.secrets.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN не задан в .env")
        self.config = config
        self.chat_id = config.secrets.telegram_chat_id
        self.bot = Bot(token=config.secrets.telegram_bot_token)
        self.dispatcher = Dispatcher()
        self._status_provider = status_provider
        self._report_provider = report_provider
        self._stop_handler = stop_handler
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Регистрирует обработчики разрешённых команд."""

        @self.dispatcher.message(Command("status"))
        async def handle_status(message: Message) -> None:
            await message.answer(self._status_provider())

        @self.dispatcher.message(Command("report"))
        async def handle_report(message: Message) -> None:
            await message.answer(self._report_provider())

        @self.dispatcher.message(Command("stop"))
        async def handle_stop(message: Message) -> None:
            await message.answer(self._stop_handler())

    async def send(self, text: str) -> None:
        """Отправляет сообщение в заданный чат."""
        if not self.chat_id:
            log.warning("telegram_chat_id_missing")
            return
        await self.bot.send_message(chat_id=self.chat_id, text=text)
        log.info("telegram_sent", length=len(text))

    async def run(self) -> None:
        """Запускает polling обработчиков команд."""
        await self.dispatcher.start_polling(self.bot)
