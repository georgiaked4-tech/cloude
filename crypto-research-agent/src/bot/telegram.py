"""Telegram-интерфейс только для отчётов и управления paper-процессом."""

from __future__ import annotations

from collections.abc import Callable

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message


def is_owner(chat_id: int | str | None, owner_chat_id: str) -> bool:
    """Сравнить отправителя с владельцем из `.env`.

    Команды `/status`, `/report` и `/stop` управляют paper-агентом, поэтому
    отвечать на них можно только владельцу: идентификатор чата сравнивается
    как строка, чтобы не зависеть от типа в апдейте Telegram.
    """

    if chat_id is None or not owner_chat_id:
        return False
    return str(chat_id).strip() == str(owner_chat_id).strip()


class TelegramReporter:
    """Отправляет сообщения и обслуживает безопасные read/control команды."""

    def __init__(
        self,
        token: str,
        chat_id: str,
        status_provider: Callable[[], str],
        report_provider: Callable[[], str],
        stop_callback: Callable[[], None],
    ) -> None:
        self.bot = Bot(token=token)
        self.chat_id = chat_id
        self.dispatcher = Dispatcher()
        self.status_provider = status_provider
        self.report_provider = report_provider
        self.stop_callback = stop_callback
        self.dispatcher.message.register(self._status, Command("status"))
        self.dispatcher.message.register(self._report, Command("report"))
        self.dispatcher.message.register(self._stop, Command("stop"))

    async def send(self, text: str) -> None:
        """Отправить уведомление владельцу без секретов и торговых действий."""

        await self.bot.send_message(self.chat_id, text)

    def _authorized(self, message: Message) -> bool:
        """Проверить, что команда пришла из чата владельца."""

        return is_owner(message.chat.id, self.chat_id)

    async def _status(self, message: Message) -> None:
        if not self._authorized(message):
            return
        await message.answer(self.status_provider())

    async def _report(self, message: Message) -> None:
        if not self._authorized(message):
            return
        await message.answer(self.report_provider())

    async def _stop(self, message: Message) -> None:
        if not self._authorized(message):
            return
        self.stop_callback()
        await message.answer("Paper-агент остановлен. Реальных ордеров не было.")

    async def run(self) -> None:
        """Запустить long polling с сетевым timeout, встроенным в aiogram."""

        await self.dispatcher.start_polling(self.bot)
