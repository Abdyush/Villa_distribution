from __future__ import annotations

from dataclasses import dataclass

from src.domain.ports import AuthorizationRepository, ChatRegistryRepository, Logger, MessagingClient
from src.domain.types import ChatId, ChatInfo, UserId


@dataclass(frozen=True)
class ListChatsResult:
    accepted: bool
    reason: str


class ListAvailableChats:
    def __init__(
        self,
        messaging_client: MessagingClient,
        chat_registry: ChatRegistryRepository,
        auth_repo: AuthorizationRepository,
        logger: Logger,
    ) -> None:
        self._messaging_client = messaging_client
        self._chat_registry = chat_registry
        self._auth_repo = auth_repo
        self._logger = logger

    async def execute(self, source_chat_id: ChatId, sender_id: UserId) -> ListChatsResult:
        if not self._auth_repo.is_authorized_sender(sender_id):
            self._logger.warning(
                f"Unauthorized sender {sender_id} tried to list available chats"
            )
            return ListChatsResult(accepted=False, reason="unauthorized_sender")

        chats = self._chat_registry.list_chats()
        if not chats:
            await self._messaging_client.send_message(
                source_chat_id,
                "Нет доступных чатов. Бот видит только те чаты, где получал сообщения.",
            )
            return ListChatsResult(accepted=True, reason="empty_list")

        filtered = [item for item in chats if item.chat_type in {"group", "supergroup", "channel"}]
        if not filtered:
            await self._messaging_client.send_message(
                source_chat_id,
                "Нет доступных групп или каналов. Бот видит только те чаты, где получал сообщения.",
            )
            return ListChatsResult(accepted=True, reason="empty_filtered_list")

        lines = ["Доступные чаты и каналы:"]
        for chat in sorted(filtered, key=lambda item: item.chat_type):
            lines.append(self._format_chat(chat))
        await self._messaging_client.send_message(source_chat_id, "\n".join(lines))
        return ListChatsResult(accepted=True, reason="ok")

    def _format_chat(self, chat: ChatInfo) -> str:
        title = chat.title or (f"@{chat.username}" if chat.username else "Без названия")
        return f"- {title}"
