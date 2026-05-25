from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.domain.types import ChatId, UserId


@dataclass(frozen=True)
class IncomingMessage:
    text: str
    source_chat_id: ChatId
    sender_id: UserId
    received_at: datetime
    message_id: int | None = None


@dataclass(frozen=True)
class BroadcastResult:
    accepted: bool
    reason: str
    sent_count: int
    failed_targets: list[ChatId]
