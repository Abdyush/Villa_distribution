from __future__ import annotations

from aiogram import Bot

from src.domain.ports import ChatInfoProvider
from src.domain.types import ChatId


class TelegramChatInfoProvider(ChatInfoProvider):
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def get_chat_title(self, chat_id: ChatId) -> str | None:
        chat = await self._bot.get_chat(chat_id)
        if chat.title:
            return chat.title
        if chat.username:
            return f"@{chat.username}"
        return None
