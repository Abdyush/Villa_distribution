from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.domain.ports import HousekeepingCommentRepository
from src.domain.types import ChatId, HousekeepingComment


class FileHousekeepingCommentRepository(HousekeepingCommentRepository):
    def __init__(self, comments_path: Path) -> None:
        self._comments_path = comments_path

    def save(self, comment: HousekeepingComment) -> None:
        comments = self._load_comments()
        comments.append(self._to_dict(comment))
        self._save_comments(comments)

    def find_active(
        self,
        chat_id: ChatId,
        room: str,
        target_date: date,
    ) -> HousekeepingComment | None:
        matches = [
            item
            for item in self._load_comments()
            if str(item.get("chat_id")) == str(chat_id)
            and str(item.get("room")) == str(room)
            and date.fromisoformat(str(item.get("start_date"))) <= target_date
            and target_date < date.fromisoformat(str(item.get("checkout_date")))
        ]
        if not matches:
            return None
        latest = max(matches, key=lambda item: str(item.get("created_at", "")))
        return self._from_dict(latest)

    def delete_for_room(self, chat_id: ChatId, room: str) -> int:
        comments = self._load_comments()
        kept = [
            item
            for item in comments
            if not (
                str(item.get("chat_id")) == str(chat_id)
                and str(item.get("room")) == str(room)
            )
        ]
        deleted_count = len(comments) - len(kept)
        if deleted_count:
            self._save_comments(kept)
        return deleted_count

    def delete_expired(self, chat_id: ChatId, target_date: date) -> int:
        comments = self._load_comments()
        kept = [
            item
            for item in comments
            if not (
                str(item.get("chat_id")) == str(chat_id)
                and date.fromisoformat(str(item.get("checkout_date"))) <= target_date
            )
        ]
        deleted_count = len(comments) - len(kept)
        if deleted_count:
            self._save_comments(kept)
        return deleted_count

    def _load_comments(self) -> list[dict[str, Any]]:
        if not self._comments_path.exists():
            return []
        with self._comments_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            return data
        return []

    def _save_comments(self, comments: list[dict[str, Any]]) -> None:
        self._comments_path.parent.mkdir(parents=True, exist_ok=True)
        with self._comments_path.open("w", encoding="utf-8") as handle:
            json.dump(comments, handle, ensure_ascii=False, indent=2)

    def _to_dict(self, comment: HousekeepingComment) -> dict[str, str]:
        return {
            "chat_id": str(comment.chat_id),
            "room": comment.room,
            "start_date": comment.start_date.isoformat(),
            "checkout_date": comment.checkout_date.isoformat(),
            "text": comment.text,
            "created_at": comment.created_at.isoformat(),
        }

    def _from_dict(self, item: dict[str, Any]) -> HousekeepingComment:
        return HousekeepingComment(
            chat_id=str(item["chat_id"]),
            room=str(item["room"]),
            start_date=date.fromisoformat(str(item["start_date"])),
            checkout_date=date.fromisoformat(str(item["checkout_date"])),
            text=str(item["text"]),
            created_at=datetime.fromisoformat(str(item["created_at"])),
        )
