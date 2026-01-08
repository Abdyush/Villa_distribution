from __future__ import annotations

from typing import Any

from src.application.dto import BroadcastResult
from src.application.use_cases.handle_incoming_distribution import (
    HandleIncomingDistribution,
)
from src.application.use_cases.manage_targets import ManageTargets
from src.application.use_cases.delete_last_distribution import DeleteLastDistribution
from src.domain.ports import ChatRegistryRepository, Logger
from src.interfaces.telegram.telegram_parser import TelegramUpdateParser


class TelegramUpdateController:
    def __init__(
        self,
        use_case: HandleIncomingDistribution,
        manage_targets: ManageTargets,
        delete_last: DeleteLastDistribution,
        chat_registry: ChatRegistryRepository,
        parser: TelegramUpdateParser,
        logger: Logger,
    ) -> None:
        self._use_case = use_case
        self._manage_targets = manage_targets
        self._delete_last = delete_last
        self._chat_registry = chat_registry
        self._parser = parser
        self._logger = logger

    async def handle_update(self, update: dict[str, Any]) -> BroadcastResult | None:
        chat_info = self._parser.parse_chat_info(update)
        if chat_info:
            self._chat_registry.upsert(chat_info)

        incoming = self._parser.parse(update)
        if not incoming:
            return None

        command = self._parse_command(incoming.text)
        if command:
            action, target_chat_id = command
            if action == "delete_last":
                result = await self._delete_last.execute(
                    incoming.source_chat_id, incoming.sender_id
                )
                self._logger.info(
                    "Delete last distribution result:"
                    f" {result.accepted} reason={result.reason}"
                    f" deleted={result.deleted_count}"
                )
                return None
            if action == "add":
                result = self._manage_targets.add_target(
                    incoming.source_chat_id, target_chat_id, incoming.sender_id
                )
            else:
                result = self._manage_targets.remove_target(
                    incoming.source_chat_id, target_chat_id, incoming.sender_id
                )
            self._logger.info(
                f"Manage targets result: {result.accepted} reason={result.reason}"
            )
            return None
        result = await self._use_case.execute(incoming)
        self._logger.info(
            f"Broadcast result: {result.accepted} sent={result.sent_count} reason={result.reason}"
        )
        return result

    def _parse_command(self, text: str) -> tuple[str, str] | None:
        parts = text.strip().split()
        if parts == ["/delete_last"]:
            return ("delete_last", "")
        if len(parts) != 2:
            return None
        if parts[0] == "/add_target":
            return ("add", parts[1])
        if parts[0] == "/remove_target":
            return ("remove", parts[1])
        return None
