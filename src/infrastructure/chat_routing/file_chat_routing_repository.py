from __future__ import annotations

import json
from pathlib import Path

from src.domain.ports import ChatRoutingRepository
from src.domain.types import ChatId


class FileChatRoutingRepository(ChatRoutingRepository):
    def __init__(self, routes_path: Path) -> None:
        self._routes_path = routes_path

    def get_targets_for_source(self, source_chat_id: ChatId) -> list[ChatId]:
        routes = self._load_routes()
        targets = routes.get(str(source_chat_id), [])
        return [str(item) for item in targets]

    def add_target(self, source_chat_id: ChatId, target_chat_id: ChatId) -> None:
        routes = self._load_routes()
        key = str(source_chat_id)
        target = str(target_chat_id)
        targets = set(routes.get(key, []))
        targets.add(target)
        routes[key] = sorted(targets)
        self._save_routes(routes)

    def remove_target(self, source_chat_id: ChatId, target_chat_id: ChatId) -> None:
        routes = self._load_routes()
        key = str(source_chat_id)
        targets = set(routes.get(key, []))
        targets.discard(str(target_chat_id))
        if targets:
            routes[key] = sorted(targets)
        else:
            routes.pop(key, None)
        self._save_routes(routes)

    def _load_routes(self) -> dict[str, list[str]]:
        if not self._routes_path.exists():
            return {}
        with self._routes_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save_routes(self, routes: dict[str, list[str]]) -> None:
        self._routes_path.parent.mkdir(parents=True, exist_ok=True)
        with self._routes_path.open("w", encoding="utf-8") as handle:
            json.dump(routes, handle, ensure_ascii=True, indent=2)
