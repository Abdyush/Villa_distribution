from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from src.application.dto import IncomingMessage
from src.domain.ports import HousekeepingCommentRepository, Logger, MessagingClient
from src.domain.types import HousekeepingComment


@dataclass(frozen=True)
class HousekeepingCommentResult:
    handled: bool
    reason: str


class HandleHousekeepingComments:
    HOUSEKEEPING_CHAT_ID = "-1001947490752"
    _MOSCOW_TZ = timezone(timedelta(hours=3))
    _COMMENT_PREFIX = "#коммент"
    _ROOM_RE = re.compile(r"^\s*(\d{3,5})(?:\s+|$)")
    _TOKEN_VS_RE = re.compile(r"(?<![а-яёa-z0-9])вс(?![а-яёa-z0-9])", re.IGNORECASE)
    _DATE_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})(?:\.(\d{2}|\d{4}))?$")

    def __init__(
        self,
        messaging_client: MessagingClient,
        comment_repo: HousekeepingCommentRepository,
        logger: Logger,
    ) -> None:
        self._messaging_client = messaging_client
        self._comment_repo = comment_repo
        self._logger = logger

    async def execute(self, incoming: IncomingMessage) -> HousekeepingCommentResult:
        if incoming.source_chat_id != self.HOUSEKEEPING_CHAT_ID:
            return HousekeepingCommentResult(False, "wrong_chat")

        expired_count = self._comment_repo.delete_expired(
            incoming.source_chat_id,
            self._local_date(incoming.received_at),
        )
        if expired_count:
            self._logger.info(f"Deleted expired housekeeping comments: {expired_count}")

        text = incoming.text.strip()
        if self._is_comment_command(text):
            return await self._handle_comment_command(incoming)

        return await self._handle_housekeeping_request(incoming)

    def _is_comment_command(self, text: str) -> bool:
        return text.casefold().startswith(self._COMMENT_PREFIX)

    async def _handle_comment_command(
        self, incoming: IncomingMessage
    ) -> HousekeepingCommentResult:
        parsed_delete = self._parse_delete_command(incoming.text)
        if parsed_delete:
            deleted_count = self._comment_repo.delete_for_room(
                incoming.source_chat_id, parsed_delete
            )
            await self._send_reply(
                incoming,
                f"Комментарий для {parsed_delete} удален."
                if deleted_count
                else f"Комментарий для {parsed_delete} не найден.",
            )
            return HousekeepingCommentResult(True, "comment_deleted")

        parsed = self._parse_create_command(incoming.text, incoming.received_at)
        if not parsed:
            await self._send_reply(
                incoming,
                "Не удалось сохранить комментарий. Формат: #коммент, номер, период, текст.",
            )
            return HousekeepingCommentResult(True, "invalid_comment_command")

        room, start_date, checkout_date, comment_text = parsed
        self._comment_repo.save(
            HousekeepingComment(
                chat_id=incoming.source_chat_id,
                room=room,
                start_date=start_date,
                checkout_date=checkout_date,
                text=comment_text,
                created_at=datetime.now(timezone.utc),
            )
        )
        active_until = checkout_date.strftime("%d.%m.%Y")
        await self._send_reply(
            incoming,
            f"Комментарий для {room} сохранен до {active_until} не включительно.",
        )
        return HousekeepingCommentResult(True, "comment_saved")

    async def _handle_housekeeping_request(
        self, incoming: IncomingMessage
    ) -> HousekeepingCommentResult:
        room = self._extract_triggered_room(incoming.text)
        if not room:
            return HousekeepingCommentResult(False, "not_housekeeping_request")

        target_date = self._local_date(incoming.received_at)
        comment = self._comment_repo.find_active(
            incoming.source_chat_id,
            room,
            target_date,
        )
        if not comment:
            return HousekeepingCommentResult(False, "no_active_comment")

        await self._send_reply(incoming, comment.text)
        return HousekeepingCommentResult(True, "comment_replied")

    def _parse_delete_command(self, text: str) -> str | None:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None

        first_line = lines[0].casefold()
        match = re.match(r"^#коммент\s+удалить\s+(\d{3,5})$", first_line)
        if match:
            return match.group(1)
        if first_line == "#коммент удалить" and len(lines) >= 2:
            room = lines[1]
            if re.fullmatch(r"\d{3,5}", room):
                return room
        return None

    def _parse_create_command(
        self, text: str, received_at: datetime
    ) -> tuple[str, date, date, str] | None:
        lines = text.splitlines()
        if len(lines) < 4 or lines[0].strip().casefold() != self._COMMENT_PREFIX:
            return None

        room = lines[1].strip()
        if not re.fullmatch(r"\d{3,5}", room):
            return None

        period = lines[2].strip()
        if "-" not in period:
            return None
        start_raw, checkout_raw = [part.strip() for part in period.split("-", 1)]
        default_year = self._local_date(received_at).year
        start_date = self._parse_date(start_raw, default_year)
        checkout_date = self._parse_date(checkout_raw, default_year)
        if not start_date or not checkout_date:
            return None
        if checkout_date <= start_date and self._date_has_no_year(checkout_raw):
            checkout_date = checkout_date.replace(year=checkout_date.year + 1)
        if checkout_date <= start_date:
            return None

        comment_text = "\n".join(lines[3:]).strip()
        if not comment_text:
            return None

        return room, start_date, checkout_date, comment_text

    def _extract_triggered_room(self, text: str) -> str | None:
        match = self._ROOM_RE.match(text)
        if not match:
            return None
        rest = text[match.end() :].casefold()
        if (
            "уборк" in rest
            or "убрать" in rest
            or "вечерний сервис" in rest
            or self._TOKEN_VS_RE.search(rest)
        ):
            return match.group(1)
        return None

    def _parse_date(self, value: str, default_year: int) -> date | None:
        match = self._DATE_RE.match(value)
        if not match:
            return None
        day = int(match.group(1))
        month = int(match.group(2))
        year_raw = match.group(3)
        year = default_year if year_raw is None else int(year_raw)
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            return None

    def _date_has_no_year(self, value: str) -> bool:
        return self._DATE_RE.match(value) is not None and value.count(".") == 1

    def _local_date(self, value: datetime) -> date:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(self._MOSCOW_TZ).date()

    async def _send_reply(self, incoming: IncomingMessage, text: str) -> None:
        if incoming.message_id is not None:
            await self._messaging_client.reply_to_message(
                incoming.source_chat_id,
                incoming.message_id,
                text,
            )
            return
        await self._messaging_client.send_message(incoming.source_chat_id, text)
