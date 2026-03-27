from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from trading_bot.adapters.notify.telegram_client import TelegramClient
from trading_bot.adapters.prices.models import Quote
from trading_bot.adapters.prices.provider import PriceProvider
from trading_bot.adapters.storage.store import EventType, StockSettingsRow, Store
from trading_bot.config import Settings
from trading_bot.observability.health import HealthState
from trading_bot.services.market_calendar import MarketWindow


@dataclass(frozen=True)
class PollerProviders:
    primary: PriceProvider
    backup: PriceProvider | None


async def run_price_poller(
    *,
    settings: Settings,
    store: Store,
    health: HealthState,
    providers: PollerProviders,
) -> None:
    logger = logging.getLogger("trading_bot.price_poller")
    window = MarketWindow(tz=settings.tz)
    notifier = _build_telegram_notifier(settings)

    while True:
        try:
            if not window.is_regular_market_open():
                await asyncio.sleep(window.seconds_until_next_open())
                continue

            symbols = await asyncio.to_thread(_get_enabled_symbols, store)
            if not symbols:
                await asyncio.sleep(min(60, settings.poll_interval_seconds))
                continue

            degraded = False
            quotes = await asyncio.to_thread(providers.primary.get_quotes, symbols)
            missing = {s for s in symbols} - {q.symbol for q in quotes}
            if missing and providers.backup is not None:
                degraded = True
                quotes += await asyncio.to_thread(
                    providers.backup.get_quotes,
                    sorted(missing),
                )

            health.mark_poll(provider=providers.primary.name, degraded=degraded)

            logger.info(
                "polled_quotes",
                extra={
                    "symbol_count": len(symbols),
                    "quote_count": len(quotes),
                    "degraded_mode": degraded,
                    "asof_max": _max_asof(quotes),
                },
            )
            if notifier is not None and quotes:
                await asyncio.to_thread(
                    _process_quote_alerts,
                    store=store,
                    settings=settings,
                    quotes=quotes,
                    notify=notifier,
                    logger=logger,
                )
            await asyncio.sleep(
                settings.degraded_poll_interval_seconds
                if degraded
                else settings.poll_interval_seconds
            )
        except Exception:
            logger.exception("poller_error")
            await asyncio.sleep(10)


def _get_enabled_symbols(store: Store) -> list[str]:
    portfolio = store.list_portfolio()
    wishlist = store.list_wishlist()
    symbols: list[str] = []
    seen: set[str] = set()
    for r in portfolio:
        if r.enabled:
            sym = r.ticker.upper()
            if sym not in seen:
                symbols.append(sym)
                seen.add(sym)
    for r in wishlist:
        if r.enabled:
            sym = r.ticker.upper()
            if sym not in seen:
                symbols.append(sym)
                seen.add(sym)
    return symbols


def _max_asof(quotes) -> str | None:
    if not quotes:
        return None
    latest: datetime = max(q.asof for q in quotes)
    return latest.isoformat()


def _build_telegram_notifier(settings: Settings) -> Callable[[str], None] | None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return None
    client = TelegramClient(bot_token=settings.telegram_bot_token)
    chat_id = settings.telegram_chat_id

    def _send(text: str) -> None:
        client.send_message(chat_id=chat_id, text=text)

    return _send


def _process_quote_alerts(
    *,
    store: Store,
    settings: Settings,
    quotes: list[Quote],
    notify: Callable[[str], None],
    logger: logging.Logger,
) -> None:
    global_settings = store.get_stock_settings("__GLOBAL__")
    if global_settings is not None and global_settings.muted:
        logger.info("alerts_suppressed_global_mute")
        return

    for quote in quotes:
        try:
            stock_settings = store.get_stock_settings(quote.symbol)
            decision = _decide_alert(
                quote=quote,
                stock_settings=stock_settings,
                default_alert_pct=settings.default_alert_pct,
                default_huge_move_pct=settings.default_huge_move_pct,
                default_cooldown_minutes=settings.default_cooldown_minutes,
            )
            if decision is None:
                continue

            event = store.create_event(
                ticker=quote.symbol,
                type=decision.event_type,
                severity=decision.severity,
                payload={
                    "direction": decision.direction,
                    "pct_change": round(decision.pct_change, 4),
                    "price": quote.price,
                    "prev_close": quote.prev_close,
                    "provider": quote.provider,
                    "threshold_pct": decision.threshold_pct,
                    "state": decision.state,
                    "asof": quote.asof.isoformat(),
                },
                event_time=quote.asof,
            )
            if _is_quiet_hours(
                now=quote.asof,
                tz=settings.tz,
                start_hhmm=settings.quiet_hours_start,
                end_hhmm=settings.quiet_hours_end,
            ):
                logger.info(
                    "alerts_suppressed_quiet_hours",
                    extra={"symbol": quote.symbol, "asof": quote.asof.isoformat()},
                )
                continue
            dedupe_key = _build_dedupe_key(
                symbol=quote.symbol,
                event_type=decision.event_type,
                direction=decision.direction,
                asof=quote.asof,
                cooldown_minutes=decision.cooldown_minutes,
            )
            should_send = store.try_mark_notification_sent(
                event_id=event.id,
                channel="telegram",
                dedupe_key=dedupe_key,
            )
            if not should_send:
                continue

            notify(_format_alert_message(quote=quote, decision=decision))
        except Exception:
            logger.exception("alert_dispatch_error", extra={"symbol": quote.symbol})


@dataclass(frozen=True)
class AlertDecision:
    event_type: EventType
    severity: int
    pct_change: float
    direction: str
    threshold_pct: float
    cooldown_minutes: int
    state: str


def _decide_alert(
    *,
    quote: Quote,
    stock_settings: StockSettingsRow | None,
    default_alert_pct: float,
    default_huge_move_pct: float,
    default_cooldown_minutes: int,
) -> AlertDecision | None:
    pct_change = quote.pct_change_from_prev_close
    if pct_change is None:
        return None
    if stock_settings is not None and stock_settings.muted:
        return None

    alert_pct = stock_settings.alert_pct if stock_settings else default_alert_pct
    huge_move_pct = (
        stock_settings.huge_move_pct if stock_settings else default_huge_move_pct
    )
    cooldown_minutes = (
        stock_settings.cooldown_minutes if stock_settings else default_cooldown_minutes
    )
    state = stock_settings.state if stock_settings else "WATCH"
    direction = "UP" if pct_change >= 0 else "DOWN"

    abs_change = abs(pct_change)
    if abs_change >= huge_move_pct:
        return AlertDecision(
            event_type=EventType.OUTLIER_MOVE,
            severity=2,
            pct_change=pct_change,
            direction=direction,
            threshold_pct=huge_move_pct,
            cooldown_minutes=cooldown_minutes,
            state=state,
        )
    if abs_change >= alert_pct:
        return AlertDecision(
            event_type=EventType.PRICE_MOVE,
            severity=1,
            pct_change=pct_change,
            direction=direction,
            threshold_pct=alert_pct,
            cooldown_minutes=cooldown_minutes,
            state=state,
        )
    return None


def _build_dedupe_key(
    *,
    symbol: str,
    event_type: EventType,
    direction: str,
    asof: datetime,
    cooldown_minutes: int,
) -> str:
    if cooldown_minutes <= 0:
        bucket = asof.isoformat()
    else:
        bucket = str(int(asof.timestamp() // (cooldown_minutes * 60)))
    return f"{event_type.value}:{symbol}:{direction}:{bucket}"


def _format_alert_message(*, quote: Quote, decision: AlertDecision) -> str:
    headline = (
        "Huge move"
        if decision.event_type is EventType.OUTLIER_MOVE
        else "Price move alert"
    )
    return "\n".join(
        [
            f"{headline}: {quote.symbol}",
            (
                f"{decision.direction} {decision.pct_change:+.2f}% "
                f"(threshold {decision.threshold_pct:.2f}%)"
            ),
            f"price: {quote.price:.2f}",
            f"state: {decision.state}",
            f"asof: {quote.asof.isoformat()}",
        ]
    )


def _is_quiet_hours(*, now: datetime, tz: str, start_hhmm: str, end_hhmm: str) -> bool:
    local_now = now.astimezone(ZoneInfo(tz))
    start_hour, start_minute = _parse_hhmm(start_hhmm)
    end_hour, end_minute = _parse_hhmm(end_hhmm)
    now_minutes = local_now.hour * 60 + local_now.minute
    start_minutes = start_hour * 60 + start_minute
    end_minutes = end_hour * 60 + end_minute

    if start_minutes == end_minutes:
        return False
    if start_minutes < end_minutes:
        return start_minutes <= now_minutes < end_minutes
    return now_minutes >= start_minutes or now_minutes < end_minutes


def _parse_hhmm(value: str) -> tuple[int, int]:
    hour, minute = value.split(":")
    return int(hour), int(minute)
