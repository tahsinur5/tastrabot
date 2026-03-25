from __future__ import annotations

import argparse
import asyncio
import logging
from asyncio import Task

from trading_bot.adapters.prices.finnhub_provider import FinnhubQuoteProvider
from trading_bot.adapters.prices.yahoo_provider import YahooQuoteProvider
from trading_bot.adapters.storage.supabase_store import SupabaseStore
from trading_bot.commands.handlers import BotContext
from trading_bot.config import Settings
from trading_bot.engine.price_poller import PollerProviders, run_price_poller
from trading_bot.observability.health import HealthState
from trading_bot.observability.logging import configure_logging
from trading_bot.telegram_bot import TelegramBotConfig, run_telegram_bot


async def _run_bot_runtime(
    *,
    settings: Settings,
    store: SupabaseStore | None,
    health: HealthState,
) -> int:
    ctx = BotContext(
        store=store,
        health=health,
        telegram_chat_id=settings.telegram_chat_id,
    )
    tasks: list[Task[None]] = []

    if store is not None:
        primary = YahooQuoteProvider()
        backup = (
            FinnhubQuoteProvider(api_key=settings.finnhub_api_key)
            if settings.finnhub_api_key
            else None
        )
        tasks.append(
            asyncio.create_task(
                run_price_poller(
                    settings=settings,
                    store=store,
                    health=health,
                    providers=PollerProviders(primary=primary, backup=backup),
                ),
                name="price_poller",
            )
        )

    tasks.append(
        asyncio.create_task(
            run_telegram_bot(
                config=TelegramBotConfig(
                    bot_token=settings.telegram_bot_token,
                    chat_id=settings.telegram_chat_id,
                ),
                ctx=ctx,
            ),
            name="telegram_bot",
        )
    )

    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    return 0


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
    if settings.supabase_url and settings.supabase_secret_key:
        store = SupabaseStore(
            supabase_url=settings.supabase_url,
            service_role_key=settings.supabase_secret_key,
        )

    if settings.telegram_bot_token and settings.telegram_chat_id:
        return asyncio.run(
            _run_bot_runtime(settings=settings, store=store, health=health)
        )

    logger.info(
        "no_runtime_configured",
        extra={"hint": "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to start the bot."},
    )
    return 0
