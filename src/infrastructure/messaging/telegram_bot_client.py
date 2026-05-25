from __future__ import annotations

from aiogram import Bot

from src.domain.ports import MessagingClient
from src.domain.types import ChatId, MessageId


class TelegramBotClient(MessagingClient):
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_message(self, chat_id: ChatId, text: str) -> MessageId:
        message = await self._bot.send_message(chat_id=chat_id, text=text)
        return int(message.message_id)

    async def reply_to_message(
        self, chat_id: ChatId, message_id: MessageId, text: str
    ) -> MessageId:
        message = await self._bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_to_message_id=message_id,
        )
        return int(message.message_id)

    async def delete_message(self, chat_id: ChatId, message_id: MessageId) -> None:
        await self._bot.delete_message(chat_id=chat_id, message_id=message_id)
