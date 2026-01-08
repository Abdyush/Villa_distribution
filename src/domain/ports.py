from __future__ import annotations

from typing import Protocol

from .types import ChatId, ChatInfo, DistributionMessage, MessageId, UserId


class MessagingClient(Protocol):
    async def send_message(self, chat_id: ChatId, text: str) -> MessageId:
        ...

    async def delete_message(self, chat_id: ChatId, message_id: MessageId) -> None:
        ...


class ChatInfoProvider(Protocol):
    async def get_chat_title(self, chat_id: ChatId) -> str | None:
        ...


class ChatRegistryRepository(Protocol):
    def upsert(self, chat_info: "ChatInfo") -> None:
        ...

    def list_chats(self) -> list["ChatInfo"]:
        ...


class ChatRoutingRepository(Protocol):
    def get_targets_for_source(self, source_chat_id: ChatId) -> list[ChatId]:
        ...

    def add_target(self, source_chat_id: ChatId, target_chat_id: ChatId) -> None:
        ...

    def remove_target(self, source_chat_id: ChatId, target_chat_id: ChatId) -> None:
        ...


class AuthorizationRepository(Protocol):
    def is_authorized_sender(self, sender_id: UserId) -> bool:
        ...


class Logger(Protocol):
    def info(self, message: str) -> None:
        ...

    def warning(self, message: str) -> None:
        ...

    def error(self, message: str) -> None:
        ...


class DistributionLogRepository(Protocol):
    def save(self, distribution: DistributionMessage) -> None:
        ...


class LastDistributionRepository(Protocol):
    def save_last(
        self,
        source_chat_id: ChatId,
        target_message_ids: dict[ChatId, MessageId],
    ) -> None:
        ...

    def get_last(self, source_chat_id: ChatId) -> dict[ChatId, MessageId]:
        ...

    def clear(self, source_chat_id: ChatId) -> None:
        ...
