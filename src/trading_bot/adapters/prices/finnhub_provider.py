from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx

from trading_bot.adapters.prices.models import Quote
from trading_bot.adapters.prices.provider import PriceProvider


class FinnhubQuoteProvider(PriceProvider):
    name = "finnhub"

    def __init__(self, *, api_key: str) -> None:
        self._api_key = api_key

    def get_quotes(self, symbols: list[str]) -> list[Quote]:
        symbols_clean = _normalize_symbols(symbols)
        quotes: list[Quote] = []
        for sym in symbols_clean:
            q = self._get_quote(sym)
            if q is not None:
                quotes.append(q)
        return quotes

    def _get_quote(self, symbol: str) -> Quote | None:
        url, params = _build_quote_request(symbol, self._api_key)
        response = httpx.request("GET", url, params=params, timeout=20)
        response.raise_for_status()
        raw = response.content
        decoded = json.loads(raw.decode("utf-8")) if raw else {}
        if not isinstance(decoded, dict):
            return None

        # Finnhub fields: c=current, pc=prev close, t=unix timestamp
        current = decoded.get("c")
        prev_close = decoded.get("pc")
        ts = decoded.get("t")
        if current in (None, 0, "") or ts in (None, 0, ""):
            return None
        asof = datetime.fromtimestamp(int(ts), tz=UTC)
        return Quote(
            symbol=symbol.upper(),
            price=float(current),
            prev_close=None if prev_close in (None, 0, "") else float(prev_close),
            asof=asof,
            provider="finnhub",
        )


def _build_quote_request(symbol: str, api_key: str) -> tuple[str, dict[str, str]]:
    return "https://finnhub.io/api/v1/quote", {"symbol": symbol, "token": api_key}


def _normalize_symbols(symbols: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for s in symbols:
        sym = s.strip().upper()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        out.append(sym)
    return out
