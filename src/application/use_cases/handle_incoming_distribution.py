from __future__ import annotations

from datetime import datetime

from src.application.dto import BroadcastResult, IncomingMessage
from src.domain.ports import (
    AuthorizationRepository,
    ChatInfoProvider,
    ChatRoutingRepository,
    DistributionLogRepository,
    LastDistributionRepository,
    Logger,
    MessagingClient,
)
from src.domain.types import DistributionMessage


class HandleIncomingDistribution:
    def __init__(
        self,
        messaging_client: MessagingClient,
        chat_routing_repo: ChatRoutingRepository,
        auth_repo: AuthorizationRepository,
        logger: Logger,
        log_repo: DistributionLogRepository | None = None,
        chat_info_provider: ChatInfoProvider | None = None,
        last_distribution_repo: LastDistributionRepository | None = None,
    ) -> None:
        self._messaging_client = messaging_client
        self._chat_routing_repo = chat_routing_repo
        self._auth_repo = auth_repo
        self._logger = logger
        self._log_repo = log_repo
        self._chat_info_provider = chat_info_provider
        self._last_distribution_repo = last_distribution_repo

    async def execute(self, incoming: IncomingMessage) -> BroadcastResult:
        if not self._auth_repo.is_authorized_sender(incoming.sender_id):
            self._logger.warning(
                f"Unauthorized sender {incoming.sender_id} in chat {incoming.source_chat_id}"
            )
            return BroadcastResult(
                accepted=False,
                reason="unauthorized_sender",
                sent_count=0,
                failed_targets=[],
            )

        targets = self._chat_routing_repo.get_targets_for_source(incoming.source_chat_id)
        if not targets:
            self._logger.info(
                f"No targets configured for source chat {incoming.source_chat_id}"
            )
            return BroadcastResult(
                accepted=False,
                reason="no_targets",
                sent_count=0,
                failed_targets=[],
            )

        if incoming.text.strip().startswith("/"):
            self._logger.info(
                f"Skipping command message from chat {incoming.source_chat_id}"
            )
            return BroadcastResult(
                accepted=False,
                reason="command_message",
                sent_count=0,
                failed_targets=[],
            )

        distribution = DistributionMessage(
            text=incoming.text,
            source_chat_id=incoming.source_chat_id,
            sender_id=incoming.sender_id,
            received_at=incoming.received_at or datetime.utcnow(),
        )
        if self._log_repo:
            self._log_repo.save(distribution)

        failed_targets: list[str] = []
        sent_message_ids: dict[str, int] = {}
        for target_chat_id in targets:
            try:
                message_id = await self._messaging_client.send_message(
                    target_chat_id, distribution.text
                )
                sent_message_ids[target_chat_id] = message_id
            except Exception as exc:
                failed_targets.append(target_chat_id)
                self._logger.error(
                    f"Failed to send to {target_chat_id}: {exc}"
                )

        if sent_message_ids and self._last_distribution_repo:
            self._last_distribution_repo.save_last(
                incoming.source_chat_id, sent_message_ids
            )

        sent_count = len(targets) - len(failed_targets)
        await self._send_summary(incoming.source_chat_id, targets, failed_targets)
        return BroadcastResult(
            accepted=True,
            reason="broadcast_complete",
            sent_count=sent_count,
            failed_targets=failed_targets,
        )

    async def _send_summary(
        self,
        source_chat_id: str,
        targets: list[str],
        failed_targets: list[str],
    ) -> None:
        if not targets:
            return
        sent_targets = [item for item in targets if item not in failed_targets]
        summary_parts = []
        sent_names = await self._resolve_target_names(sent_targets)
        summary_parts.append(f"Переслал в: {', '.join(sent_names)}")
        if failed_targets:
            failed_names = await self._resolve_target_names(failed_targets)
            summary_parts.append(f"Не удалось: {', '.join(failed_names)}")
        summary_text = "\n".join(summary_parts)
        await self._messaging_client.send_message(source_chat_id, summary_text)

    async def _resolve_target_names(self, targets: list[str]) -> list[str]:
        if not targets:
            return []
        if not self._chat_info_provider:
            return targets
        resolved: list[str] = []
        for target in targets:
            try:
                title = await self._chat_info_provider.get_chat_title(target)
                resolved.append(title or target)
            except Exception as exc:
                self._logger.warning(
                    f"Failed to resolve chat title for {target}: {exc}"
                )
                resolved.append(target)
        return resolved
