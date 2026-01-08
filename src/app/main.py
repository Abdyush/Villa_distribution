from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

import aiogram
from aiogram import Bot, Dispatcher, Router
from aiogram.types import BotCommand, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.application.use_cases.handle_incoming_distribution import (
    HandleIncomingDistribution,
)
from src.application.use_cases.delete_last_distribution import DeleteLastDistribution
from src.application.use_cases.manage_targets import ManageTargets
from src.infrastructure.auth.file_auth_repository import FileAuthorizationRepository
from src.infrastructure.chat_routing.file_chat_routing_repository import (
    FileChatRoutingRepository,
)
from src.infrastructure.chat_registry.file_chat_registry_repository import (
    FileChatRegistryRepository,
)
from src.infrastructure.logging.noop_distribution_log_repository import (
    NoopDistributionLogRepository,
)
from src.infrastructure.distribution.file_last_distribution_repository import (
    FileLastDistributionRepository,
)
from src.infrastructure.logging.std_logger import StdLogger
from src.infrastructure.messaging.telegram_chat_info_provider import (
    TelegramChatInfoProvider,
)
from src.infrastructure.messaging.telegram_bot_client import TelegramBotClient
from src.interfaces.telegram.telegram_controller import TelegramUpdateController
from src.interfaces.telegram.telegram_parser import TelegramUpdateParser


def _data_path(name: str) -> Path:
    return PROJECT_ROOT / "data" / name


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def build_controller(bot: Bot, logger: StdLogger) -> TelegramUpdateController:
    messaging_client = TelegramBotClient(bot)
    chat_info_provider = TelegramChatInfoProvider(bot)

    chat_repo = FileChatRoutingRepository(_data_path("routes.json"))
    chat_registry = FileChatRegistryRepository(_data_path("chat_registry.json"))
    auth_repo = FileAuthorizationRepository(_data_path("authorized_senders.json"))
    log_repo = NoopDistributionLogRepository()
    last_distribution_repo = FileLastDistributionRepository(
        _data_path("last_distribution.json")
    )

    use_case = HandleIncomingDistribution(
        messaging_client=messaging_client,
        chat_routing_repo=chat_repo,
        auth_repo=auth_repo,
        logger=logger,
        log_repo=log_repo,
        chat_info_provider=chat_info_provider,
        last_distribution_repo=last_distribution_repo,
    )
    manage_targets = ManageTargets(
        chat_routing_repo=chat_repo,
        auth_repo=auth_repo,
        logger=logger,
    )
    delete_last = DeleteLastDistribution(
        messaging_client=messaging_client,
        auth_repo=auth_repo,
        last_distribution_repo=last_distribution_repo,
        logger=logger,
        chat_info_provider=chat_info_provider,
    )
    parser = TelegramUpdateParser()
    return TelegramUpdateController(
        use_case=use_case,
        manage_targets=manage_targets,
        delete_last=delete_last,
        chat_registry=chat_registry,
        parser=parser,
        logger=logger,
    )


async def main() -> None:
    load_dotenv()
    bot_token = _required_env("BOT_TOKEN")
    bot = Bot(token=bot_token)
    logger = StdLogger()
    logger.info(f"Bot starting. aiogram version={aiogram.__version__}")
    logging.basicConfig(level=logging.INFO)
    await bot.set_my_commands(
        [
            BotCommand(
                command="delete_last",
                description="Удалить последнее пересланное сообщение",
            ),
            BotCommand(
                command="select_chats",
                description="Выбрать чаты для пересылки",
            ),
        ]
    )
    controller = build_controller(bot, logger)
    chat_repo = FileChatRoutingRepository(_data_path("routes.json"))
    chat_registry = FileChatRegistryRepository(_data_path("chat_registry.json"))
    auth_repo = FileAuthorizationRepository(_data_path("authorized_senders.json"))

    dp = Dispatcher()
    router = Router()

    def _chat_display_name(chat_id: str, title: str | None, username: str | None) -> str:
        if title:
            return title
        if username:
            return f"@{username}"
        return chat_id

    def _build_inline_targets_keyboard(source_chat_id: str) -> InlineKeyboardBuilder:
        builder = InlineKeyboardBuilder()
        selected = set(chat_repo.get_targets_for_source(source_chat_id))
        chats = [
            chat
            for chat in chat_registry.list_chats()
            if chat.chat_type in {"group", "supergroup", "channel"}
        ]
        for chat in chats:
            marker = "[x]" if chat.chat_id in selected else "[ ]"
            title = _chat_display_name(chat.chat_id, chat.title, chat.username)
            builder.button(
                text=f"{marker} {title}",
                callback_data=f"toggle:{chat.chat_id}",
            )
        builder.button(text="Done", callback_data="done")
        builder.adjust(1)
        return builder

    def _is_authorized(sender_id: int | None) -> bool:
        if sender_id is None:
            return False
        return auth_repo.is_authorized_sender(str(sender_id))

    @router.message()
    async def on_message(message: Message) -> None:
        logger.info(
            "Message received"
            f" chat_id={message.chat.id}"
            f" sender_id={getattr(message.from_user, 'id', None)}"
            f" text={message.text!r}"
        )
        payload: dict[str, Any] = {
            "update_id": message.message_id,
            "message": message.model_dump(),
        }
        await controller.handle_update(payload)
        if message.text == "/select_chats":
            if not _is_authorized(getattr(message.from_user, "id", None)):
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="No access.",
                )
                return
            await bot.send_message(
                chat_id=message.chat.id,
                text="Choose target chats:",
                reply_markup=_build_inline_targets_keyboard(
                    str(message.chat.id)
                ).as_markup(),
            )

    @router.channel_post()
    async def on_channel_post(message: Message) -> None:
        logger.info(
            "Channel post received"
            f" chat_id={message.chat.id}"
            f" text={message.text!r}"
        )
        payload: dict[str, Any] = {
            "update_id": message.message_id,
            "channel_post": message.model_dump(),
        }
        await controller.handle_update(payload)

    @router.callback_query()
    async def on_callback(callback: CallbackQuery) -> None:
        data = callback.data or ""
        message = callback.message
        if not message:
            await callback.answer()
            return
        if not _is_authorized(getattr(callback.from_user, "id", None)):
            await callback.answer("No access.", show_alert=True)
            return
        source_chat_id = str(message.chat.id)
        if data == "done":
            await message.delete()
            await callback.answer("Done")
            return
        if data.startswith("toggle:"):
            target_chat_id = data.split(":", 1)[1]
            current = set(chat_repo.get_targets_for_source(source_chat_id))
            if target_chat_id in current:
                chat_repo.remove_target(source_chat_id, target_chat_id)
            else:
                chat_repo.add_target(source_chat_id, target_chat_id)
            keyboard = _build_inline_targets_keyboard(source_chat_id).as_markup()
            await message.edit_reply_markup(reply_markup=keyboard)
            await callback.answer()
            return
        await callback.answer()

    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=False)
    me = await bot.get_me()
    logger.info(f"Bot ready. username=@{me.username} id={me.id}")
    logger.info("Bot started. Polling for updates.")
    await dp.start_polling(
        bot, allowed_updates=["message", "channel_post", "callback_query"]
    )


if __name__ == "__main__":
    asyncio.run(main())
