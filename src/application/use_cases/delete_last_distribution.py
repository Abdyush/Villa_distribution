from __future__ import annotations

from dataclasses import dataclass

from src.domain.ports import (
    AuthorizationRepository,
    ChatInfoProvider,
    LastDistributionRepository,
    Logger,
    MessagingClient,
)
from src.domain.types import ChatId, MessageId, UserId


@dataclass(frozen=True)
class DeleteLastResult:
    accepted: bool
    reason: str
    deleted_count: int
    failed_targets: list[ChatId]


class DeleteLastDistribution:
    def __init__(
        self,
        messaging_client: MessagingClient,
        auth_repo: AuthorizationRepository,
        last_distribution_repo: LastDistributionRepository,
        logger: Logger,
        chat_info_provider: ChatInfoProvider | None = None,
    ) -> None:
        self._messaging_client = messaging_client
        self._auth_repo = auth_repo
        self._last_distribution_repo = last_distribution_repo
        self._logger = logger
        self._chat_info_provider = chat_info_provider

    async def execute(
        self, source_chat_id: ChatId, sender_id: UserId
    ) -> DeleteLastResult:
        if not self._auth_repo.is_authorized_sender(sender_id):
            self._logger.warning(
                f"Unauthorized sender {sender_id} tried to delete last distribution"
            )
            return DeleteLastResult(
                accepted=False,
                reason="unauthorized_sender",
                deleted_count=0,
                failed_targets=[],
            )

        last_sent = self._last_distribution_repo.get_last(source_chat_id)
        if not last_sent:
            await self._messaging_client.send_message(
                source_chat_id, "Nothing to delete."
            )
            return DeleteLastResult(
                accepted=False,
                reason="no_last_distribution",
                deleted_count=0,
                failed_targets=[],
            )

        failed: dict[ChatId, MessageId] = {}
        for chat_id, message_id in last_sent.items():
            try:
                await self._messaging_client.delete_message(chat_id, message_id)
            except Exception as exc:
                failed[chat_id] = message_id
                self._logger.error(
                    f"Failed to delete message {message_id} in {chat_id}: {exc}"
                )

        deleted_count = len(last_sent) - len(failed)
        if failed:
            self._last_distribution_repo.save_last(source_chat_id, failed)
        else:
            self._last_distribution_repo.clear(source_chat_id)

        summary_parts = [f"Deleted in {deleted_count} chats."]
        if failed:
            failed_names = await self._resolve_target_names(list(failed.keys()))
            summary_parts.append(f"Failed: {', '.join(failed_names)}")
        await self._messaging_client.send_message(
            source_chat_id, "\n".join(summary_parts)
        )

        return DeleteLastResult(
            accepted=True,
            reason="delete_complete",
            deleted_count=deleted_count,
            failed_targets=list(failed.keys()),
        )

    async def _resolve_target_names(self, targets: list[ChatId]) -> list[str]:
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
