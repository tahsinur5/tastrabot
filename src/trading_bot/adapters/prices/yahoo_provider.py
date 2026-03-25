from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any

from trading_bot.adapters.prices.models import Quote
from trading_bot.adapters.prices.provider import PriceProvider


class YahooQuoteProvider(PriceProvider):
    name = "yahoo"

    def get_quotes(self, symbols: list[str]) -> list[Quote]:
        symbols_clean = _normalize_symbols(symbols)
        if not symbols_clean:
            return []

        url = _build_quote_url(symbols_clean)
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()

        decoded = json.loads(raw.decode("utf-8")) if raw else {}
        result = (
            decoded.get("quoteResponse", {}).get("result", [])
            if isinstance(decoded, dict)
            else []
        )
        if not isinstance(result, list):
            return []

        quotes: list[Quote] = []
        for r in result:
            q = _row_to_quote(r)
            if q is not None:
                quotes.append(q)
        return quotes


def _build_quote_url(symbols: list[str]) -> str:
    base = "https://query1.finance.yahoo.com/v7/finance/quote"
    params = {"symbols": ",".join(symbols)}
    return base + "?" + urllib.parse.urlencode(params)


def _normalize_symbols(symbols: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for s in symbols:
        sym = s.strip().upper()
        if not sym:
            continue
        if sym in seen:
            continue
        seen.add(sym)
        out.append(sym)
    return out


def _row_to_quote(row: Any) -> Quote | None:
    if not isinstance(row, dict):
        return None
    symbol = row.get("symbol")
    price = row.get("regularMarketPrice")
    prev_close = row.get("regularMarketPreviousClose")
    ts = row.get("regularMarketTime")
    if not symbol or price in (None, "") or ts in (None, ""):
        return None
    asof = datetime.fromtimestamp(int(ts), tz=UTC)
    return Quote(
        symbol=str(symbol).upper(),
        price=float(price),
        prev_close=None if prev_close in (None, "") else float(prev_close),
        asof=asof,
        provider="yahoo",
    )
