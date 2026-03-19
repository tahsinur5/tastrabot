from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from trading_bot.adapters.notify.telegram_client import TelegramClient
from trading_bot.commands.handlers import BotContext, handle_command


@dataclass(frozen=True)
class TelegramBotConfig:
    bot_token: str
    chat_id: str


def run_telegram_bot(
    *,
    config: TelegramBotConfig,
    ctx: BotContext,
    poll_timeout_seconds: int = 30,
) -> None:
    logger = logging.getLogger("trading_bot.telegram")
    client = TelegramClient(bot_token=config.bot_token)
    offset: int | None = None

    while True:
        try:
            updates = client.get_updates(offset=offset, timeout=poll_timeout_seconds)
            for update in updates:
                offset = update.update_id + 1
                message = update.message
                chat = message.get("chat") or {}
                chat_id = str(chat.get("id", ""))
                if chat_id != config.chat_id:
                    continue
                text = message.get("text")
                if not isinstance(text, str):
                    continue
                if not text.strip().startswith("/"):
                    continue
                reply = handle_command(ctx, text)
                client.send_message(chat_id=config.chat_id, text=reply)
        except Exception:
            logger.exception("telegram_loop_error")
            time.sleep(5)
