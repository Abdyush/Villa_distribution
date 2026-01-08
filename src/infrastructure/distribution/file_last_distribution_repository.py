from __future__ import annotations

import json
from pathlib import Path

from src.domain.ports import LastDistributionRepository
from src.domain.types import ChatId, MessageId


class FileLastDistributionRepository(LastDistributionRepository):
    def __init__(self, path: Path) -> None:
        self._path = path

    def save_last(
        self,
        source_chat_id: ChatId,
        target_message_ids: dict[ChatId, MessageId],
    ) -> None:
        data = self._load()
        data[str(source_chat_id)] = {
            str(chat_id): int(message_id)
            for chat_id, message_id in target_message_ids.items()
        }
        self._save(data)

    def get_last(self, source_chat_id: ChatId) -> dict[ChatId, MessageId]:
        data = self._load()
        raw = data.get(str(source_chat_id), {})
        return {str(chat_id): int(message_id) for chat_id, message_id in raw.items()}

    def clear(self, source_chat_id: ChatId) -> None:
        data = self._load()
        if str(source_chat_id) in data:
            data.pop(str(source_chat_id), None)
            self._save(data)

    def _load(self) -> dict[str, dict[str, int]]:
        if not self._path.exists():
            return {}
        with self._path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save(self, data: dict[str, dict[str, int]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=True, indent=2)
