from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import patch

from trading_bot.adapters.prices.finnhub_provider import FinnhubQuoteProvider
from trading_bot.adapters.prices.yahoo_provider import YahooQuoteProvider


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_yahoo_provider_parses_quote_batch() -> None:
    provider = YahooQuoteProvider()
    ts = int(datetime(2026, 3, 23, 14, 30, 0, tzinfo=UTC).timestamp())
    body = json.dumps(
        {
            "quoteResponse": {
                "result": [
                    {
                        "symbol": "AAPL",
                        "regularMarketPrice": 100.0,
                        "regularMarketPreviousClose": 95.0,
                        "regularMarketTime": ts,
                    }
                ]
            }
        }
    ).encode("utf-8")

    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        return _FakeResponse(body)

    with patch("urllib.request.urlopen", fake_urlopen):
        quotes = provider.get_quotes(["aapl", "AAPL"])

    assert "query1.finance.yahoo.com" in captured["url"]
    assert "symbols=AAPL" in captured["url"]
    assert len(quotes) == 1
    assert quotes[0].symbol == "AAPL"
    assert quotes[0].price == 100.0
    assert quotes[0].prev_close == 95.0
    assert quotes[0].provider == "yahoo"


def test_finnhub_provider_parses_quote() -> None:
    provider = FinnhubQuoteProvider(api_key="k")
    ts = int(datetime(2026, 3, 23, 14, 30, 0, tzinfo=UTC).timestamp())
    body = json.dumps({"c": 10.0, "pc": 9.5, "t": ts}).encode("utf-8")
    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        return _FakeResponse(body)

    with patch("urllib.request.urlopen", fake_urlopen):
        quotes = provider.get_quotes(["msft"])

    assert "finnhub.io/api/v1/quote" in captured["url"]
    assert "symbol=MSFT" in captured["url"]
    assert "token=k" in captured["url"]
    assert len(quotes) == 1
    assert quotes[0].symbol == "MSFT"
    assert quotes[0].price == 10.0
    assert quotes[0].prev_close == 9.5
    assert quotes[0].provider == "finnhub"
