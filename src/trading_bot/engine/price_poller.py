from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime

from trading_bot.adapters.prices.provider import PriceProvider
from trading_bot.adapters.storage.store import Store
from trading_bot.config import Settings
from trading_bot.engine.market_time import MarketWindow
from trading_bot.observability.health import HealthState


@dataclass(frozen=True)
class PollerProviders:
    primary: PriceProvider
    backup: PriceProvider | None


def run_price_poller(
    *,
    settings: Settings,
    store: Store,
    health: HealthState,
    providers: PollerProviders,
) -> None:
    logger = logging.getLogger("trading_bot.price_poller")
    window = MarketWindow(tz=settings.tz)

    while True:
        try:
            if not window.is_regular_market_open():
                time.sleep(min(60, settings.poll_interval_seconds))
                continue

            symbols = _get_enabled_symbols(store)
            if not symbols:
                time.sleep(min(60, settings.poll_interval_seconds))
                continue

            degraded = False
            quotes = providers.primary.get_quotes(symbols)
            missing = {s for s in symbols} - {q.symbol for q in quotes}
            if missing and providers.backup is not None:
                degraded = True
                quotes += providers.backup.get_quotes(sorted(missing))

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
            time.sleep(
                settings.degraded_poll_interval_seconds
                if degraded
                else settings.poll_interval_seconds
            )
        except Exception:
            logger.exception("poller_error")
            time.sleep(10)


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
