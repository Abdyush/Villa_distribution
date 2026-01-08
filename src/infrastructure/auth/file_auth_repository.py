from __future__ import annotations

import json
from pathlib import Path

from src.domain.ports import AuthorizationRepository
from src.domain.types import UserId


class FileAuthorizationRepository(AuthorizationRepository):
    def __init__(self, authorized_path: Path) -> None:
        self._authorized_path = authorized_path

    def is_authorized_sender(self, sender_id: UserId) -> bool:
        allowed = self._load_ids()
        return str(sender_id) in allowed

    def _load_ids(self) -> set[str]:
        if not self._authorized_path.exists():
            return set()
        with self._authorized_path.open("r", encoding="utf-8") as handle:
            values = json.load(handle)
        return {str(item) for item in values}
