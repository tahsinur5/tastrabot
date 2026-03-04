from __future__ import annotations

import io
import json
from unittest.mock import patch

from trading_bot.adapters.storage.supabase_store import SupabaseStore


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _lower_headers(headers: dict[str, str]) -> dict[str, str]:
    return {k.lower(): v for k, v in headers.items()}


def test_list_portfolio_builds_request() -> None:
    store = SupabaseStore(supabase_url="https://example.supabase.co", service_role_key="k")
    body = json.dumps(
        [{"ticker": "AAPL", "quantity": 1, "enabled": True}]
    ).encode("utf-8")

    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        captured["headers"] = _lower_headers(dict(req.headers))
        captured["method"] = req.get_method()
        return _FakeResponse(body)

    with patch("urllib.request.urlopen", fake_urlopen):
        rows = store.list_portfolio()

    assert captured["method"] == "GET"
    assert "rest/v1/portfolio" in captured["url"]
    assert "enabled=eq.true" in captured["url"]
    assert captured["headers"]["apikey"] == "k"
    assert captured["headers"]["authorization"] == "Bearer k"
    assert rows[0].ticker == "AAPL"


def test_list_wishlist_parses_target_price_nullable() -> None:
    store = SupabaseStore(supabase_url="https://example.supabase.co", service_role_key="k")
    body = json.dumps(
        [
            {"ticker": "MSFT", "target_price": None, "enabled": True},
            {"ticker": "NVDA", "target_price": "950.50", "enabled": True},
        ]
    ).encode("utf-8")

    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        return _FakeResponse(body)

    with patch("urllib.request.urlopen", fake_urlopen):
        rows = store.list_wishlist()

    assert "rest/v1/wishlist" in captured["url"]
    assert "enabled=eq.true" in captured["url"]
    assert rows[0].ticker == "MSFT"
    assert rows[0].target_price is None
    assert rows[1].ticker == "NVDA"
    assert rows[1].target_price == 950.50


def test_get_stock_settings_none_when_missing() -> None:
    store = SupabaseStore(supabase_url="https://example.supabase.co", service_role_key="k")
    body = b"[]"

    def fake_urlopen(req, timeout=0):
        return _FakeResponse(body)

    with patch("urllib.request.urlopen", fake_urlopen):
        row = store.get_stock_settings("AAPL")

    assert row is None


def test_get_stock_settings_applies_defaults() -> None:
    store = SupabaseStore(supabase_url="https://example.supabase.co", service_role_key="k")
    body = json.dumps([{"ticker": "AAPL"}]).encode("utf-8")

    def fake_urlopen(req, timeout=0):
        return _FakeResponse(body)

    with patch("urllib.request.urlopen", fake_urlopen):
        row = store.get_stock_settings("aapl")

    assert row is not None
    assert row.ticker == "AAPL"
    assert row.state == "WATCH"
    assert row.alert_pct == 2.0
    assert row.huge_move_pct == 5.0
    assert row.cooldown_minutes == 60
    assert row.news_level == "NORMAL"
    assert row.muted is False


def test_upsert_stock_settings_posts_json() -> None:
    store = SupabaseStore(supabase_url="https://example.supabase.co/", service_role_key="k")
    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        captured["headers"] = _lower_headers(dict(req.headers))
        captured["method"] = req.get_method()
        captured["data"] = req.data
        return _FakeResponse(b"")

    with patch("urllib.request.urlopen", fake_urlopen):
        store.upsert_stock_settings("tsla", state="BUY", muted=True)

    assert captured["method"] == "POST"
    assert "rest/v1/stock_settings" in captured["url"]
    assert "on_conflict=ticker" in captured["url"]
    assert captured["headers"]["content-type"] == "application/json"
    payload = json.loads(captured["data"].decode("utf-8"))
    assert payload["ticker"] == "TSLA"
    assert payload["state"] == "BUY"
    assert payload["muted"] is True


def test_http_error_includes_body() -> None:
    import urllib.error

    store = SupabaseStore(supabase_url="https://example.supabase.co", service_role_key="k")

    def fake_urlopen(req, timeout=0):
        fp = io.BytesIO(b'{"message":"nope"}')
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", hdrs=None, fp=fp)

    with patch("urllib.request.urlopen", fake_urlopen):
        try:
            store.list_portfolio()
        except RuntimeError as e:
            assert "Supabase HTTP 401" in str(e)
            assert "nope" in str(e)
        else:
            raise AssertionError("Expected RuntimeError")
