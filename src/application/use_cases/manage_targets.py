from __future__ import annotations

from dataclasses import dataclass

from src.domain.ports import AuthorizationRepository, ChatRoutingRepository, Logger
from src.domain.types import ChatId, UserId


@dataclass(frozen=True)
class ManageTargetsResult:
    accepted: bool
    reason: str


class ManageTargets:
    def __init__(
        self,
        chat_routing_repo: ChatRoutingRepository,
        auth_repo: AuthorizationRepository,
        logger: Logger,
    ) -> None:
        self._chat_routing_repo = chat_routing_repo
        self._auth_repo = auth_repo
        self._logger = logger

    def add_target(
        self, source_chat_id: ChatId, target_chat_id: ChatId, sender_id: UserId
    ) -> ManageTargetsResult:
        if not self._auth_repo.is_authorized_sender(sender_id):
            self._logger.warning(
                f"Unauthorized sender {sender_id} tried to add target {target_chat_id}"
            )
            return ManageTargetsResult(accepted=False, reason="unauthorized_sender")

        self._chat_routing_repo.add_target(source_chat_id, target_chat_id)
        self._logger.info(
            f"Added target {target_chat_id} for source {source_chat_id}"
        )
        return ManageTargetsResult(accepted=True, reason="target_added")

    def remove_target(
        self, source_chat_id: ChatId, target_chat_id: ChatId, sender_id: UserId
    ) -> ManageTargetsResult:
        if not self._auth_repo.is_authorized_sender(sender_id):
            self._logger.warning(
                f"Unauthorized sender {sender_id} tried to remove target {target_chat_id}"
            )
            return ManageTargetsResult(accepted=False, reason="unauthorized_sender")

        self._chat_routing_repo.remove_target(source_chat_id, target_chat_id)
        self._logger.info(
            f"Removed target {target_chat_id} for source {source_chat_id}"
        )
        return ManageTargetsResult(accepted=True, reason="target_removed")
