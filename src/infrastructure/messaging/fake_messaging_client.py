from __future__ import annotations

from src.domain.ports import MessagingClient
from src.domain.types import ChatId, MessageId


class FakeMessagingClient(MessagingClient):
    def __init__(self) -> None:
        self.sent: list[tuple[ChatId, str]] = []
        self.deleted: list[tuple[ChatId, MessageId]] = []

    async def send_message(self, chat_id: ChatId, text: str) -> MessageId:
        self.sent.append((chat_id, text))
        return len(self.sent)

    async def delete_message(self, chat_id: ChatId, message_id: MessageId) -> None:
        self.deleted.append((chat_id, message_id))
