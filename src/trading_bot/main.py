from __future__ import annotations

import argparse
import logging

from trading_bot.adapters.storage.supabase_store import SupabaseStore
from trading_bot.commands.handlers import BotContext
from trading_bot.config import Settings
from trading_bot.observability.health import HealthState
from trading_bot.observability.logging import configure_logging
from trading_bot.telegram_bot import TelegramBotConfig, run_telegram_bot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trading_bot")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate settings and exit (no external calls).",
    )
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    configure_logging(settings.log_level)

    logger = logging.getLogger("trading_bot")
    health = HealthState()
    logger.info(
        "startup",
        extra={
            "tz": settings.tz,
            "poll_interval_seconds": settings.poll_interval_seconds,
        },
    )

    if args.check:
        logger.info("check_ok", extra={"degraded_mode": health.degraded_mode})
        return 0

    store: SupabaseStore | None = None
    if settings.supabase_url and settings.supabase_service_role_key:
        store = SupabaseStore(
            supabase_url=settings.supabase_url,
            service_role_key=settings.supabase_service_role_key,
        )

    if settings.telegram_bot_token and settings.telegram_chat_id:
        ctx = BotContext(
            store=store,
            health=health,
            telegram_chat_id=settings.telegram_chat_id,
        )
        run_telegram_bot(
            config=TelegramBotConfig(
                bot_token=settings.telegram_bot_token,
                chat_id=settings.telegram_chat_id,
            ),
            ctx=ctx,
        )
        return 0

    logger.info(
        "no_runtime_configured",
        extra={"hint": "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to start the bot."},
    )
    return 0
