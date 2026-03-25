from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import UTC, datetime

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
        url = _build_quote_url(symbol, self._api_key)
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
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


def _build_quote_url(symbol: str, api_key: str) -> str:
    base = "https://finnhub.io/api/v1/quote"
    params = {"symbol": symbol, "token": api_key}
    return base + "?" + urllib.parse.urlencode(params)


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
