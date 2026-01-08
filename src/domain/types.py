from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


ChatId = str
UserId = str
MessageId = int


@dataclass(frozen=True)
class ChatInfo:
    chat_id: ChatId
    title: str | None
    chat_type: str
    username: str | None = None


@dataclass(frozen=True)
class DistributionMessage:
    text: str
    source_chat_id: ChatId
    sender_id: UserId
    received_at: datetime
