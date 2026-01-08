from __future__ import annotations

from datetime import datetime
from typing import Any

from src.application.dto import IncomingMessage
from src.domain.types import ChatInfo


class TelegramUpdateParser:
    def parse(self, update: dict[str, Any]) -> IncomingMessage | None:
        message = update.get("message") or update.get("channel_post")
        if not message:
            return None

        text = message.get("text")
        if not text:
            return None

        chat = message.get("chat") or {}
        sender = message.get("from") or message.get("from_user") or {}
        timestamp = message.get("date")

        return IncomingMessage(
            text=text,
            source_chat_id=str(chat.get("id", "")),
            sender_id=str(sender.get("id", "")),
            received_at=datetime.utcfromtimestamp(timestamp) if timestamp else datetime.utcnow(),
        )

    def parse_chat_info(self, update: dict[str, Any]) -> ChatInfo | None:
        message = update.get("message") or update.get("channel_post")
        if not message:
            return None
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        if not chat_id:
            return None
        title = chat.get("title")
        if not title and chat.get("type") == "private":
            first = chat.get("first_name") or ""
            last = chat.get("last_name") or ""
            title = (first + " " + last).strip() or None
        username = chat.get("username")
        chat_type = chat.get("type") or "unknown"
        return ChatInfo(
            chat_id=chat_id,
            title=title,
            chat_type=chat_type,
            username=username,
        )
