from __future__ import annotations

import json
from pathlib import Path

from src.domain.ports import ChatRegistryRepository
from src.domain.types import ChatId, ChatInfo


class FileChatRegistryRepository(ChatRegistryRepository):
    def __init__(self, registry_path: Path) -> None:
        self._registry_path = registry_path

    def upsert(self, chat_info: ChatInfo) -> None:
        data = self._load()
        data[str(chat_info.chat_id)] = {
            "chat_id": str(chat_info.chat_id),
            "title": chat_info.title,
            "chat_type": chat_info.chat_type,
            "username": chat_info.username,
        }
        self._save(data)

    def list_chats(self) -> list[ChatInfo]:
        data = self._load()
        result: list[ChatInfo] = []
        for item in data.values():
            result.append(
                ChatInfo(
                    chat_id=str(item.get("chat_id", "")),
                    title=item.get("title"),
                    chat_type=item.get("chat_type") or "unknown",
                    username=item.get("username"),
                )
            )
        return result

    def _load(self) -> dict[str, dict[str, str | None]]:
        if not self._registry_path.exists():
            return {}
        with self._registry_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save(self, data: dict[str, dict[str, str | None]]) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        with self._registry_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=True, indent=2)
