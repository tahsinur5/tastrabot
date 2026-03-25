from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID

import httpx

from trading_bot.adapters.storage.store import EventType
from trading_bot.adapters.storage.supabase_store import SupabaseHttpError, SupabaseStore


def _lower_headers(headers: dict[str, str]) -> dict[str, str]:
    return {k.lower(): v for k, v in headers.items()}


def test_list_portfolio_builds_request() -> None:
    store = SupabaseStore(
        supabase_url="https://example.supabase.co", service_role_key="k"
    )
    body = json.dumps([{"ticker": "AAPL", "quantity": 1, "enabled": True}]).encode(
        "utf-8"
    )

    captured = {}

    def fake_request(method, url, params=None, headers=None, **kwargs):
        full_url = str(httpx.URL(url, params=params or {}))
        captured["url"] = full_url
        captured["headers"] = _lower_headers(dict(headers or {}))
        captured["method"] = method
        request = httpx.Request(method, full_url)
        return httpx.Response(200, content=body, request=request)

    with patch("httpx.request", fake_request):
        rows = store.list_portfolio()

    assert captured["method"] == "GET"
    assert "rest/v1/portfolio" in captured["url"]
    assert "enabled=eq.true" in captured["url"]
    assert captured["headers"]["apikey"] == "k"
    assert captured["headers"]["authorization"] == "Bearer k"
    assert rows[0].ticker == "AAPL"


def test_list_wishlist_parses_target_price_nullable() -> None:
    store = SupabaseStore(
        supabase_url="https://example.supabase.co", service_role_key="k"
    )
    body = json.dumps(
        [
            {"ticker": "MSFT", "target_price": None, "enabled": True},
            {"ticker": "NVDA", "target_price": "950.50", "enabled": True},
        ]
    ).encode("utf-8")

    captured = {}

    def fake_request(method, url, params=None, **kwargs):
        captured["url"] = str(httpx.URL(url, params=params or {}))
        request = httpx.Request(method, captured["url"])
        return httpx.Response(200, content=body, request=request)

    with patch("httpx.request", fake_request):
        rows = store.list_wishlist()

    assert "rest/v1/wishlist" in captured["url"]
    assert "enabled=eq.true" in captured["url"]
    assert rows[0].ticker == "MSFT"
    assert rows[0].target_price is None
    assert rows[1].ticker == "NVDA"
    assert rows[1].target_price == 950.50


def test_get_stock_settings_none_when_missing() -> None:
    store = SupabaseStore(
        supabase_url="https://example.supabase.co", service_role_key="k"
    )
    body = b"[]"

    def fake_request(method, url, params=None, **kwargs):
        full_url = str(httpx.URL(url, params=params or {}))
        request = httpx.Request(method, full_url)
        return httpx.Response(200, content=body, request=request)

    with patch("httpx.request", fake_request):
        row = store.get_stock_settings("AAPL")

    assert row is None


def test_get_stock_settings_applies_defaults() -> None:
    store = SupabaseStore(
        supabase_url="https://example.supabase.co", service_role_key="k"
    )
    body = json.dumps([{"ticker": "AAPL"}]).encode("utf-8")

    def fake_request(method, url, params=None, **kwargs):
        full_url = str(httpx.URL(url, params=params or {}))
        request = httpx.Request(method, full_url)
        return httpx.Response(200, content=body, request=request)

    with patch("httpx.request", fake_request):
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
    store = SupabaseStore(
        supabase_url="https://example.supabase.co/", service_role_key="k"
    )
    captured = {}

    def fake_request(method, url, params=None, headers=None, content=None, **kwargs):
        captured["url"] = str(httpx.URL(url, params=params or {}))
        captured["headers"] = _lower_headers(dict(headers or {}))
        captured["method"] = method
        captured["data"] = content
        request = httpx.Request(method, captured["url"])
        return httpx.Response(200, content=b"", request=request)

    with patch("httpx.request", fake_request):
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
    store = SupabaseStore(
        supabase_url="https://example.supabase.co", service_role_key="k"
    )

    def fake_request(method, url, params=None, **kwargs):
        full_url = str(httpx.URL(url, params=params or {}))
        request = httpx.Request(method, full_url)
        return httpx.Response(401, content=b'{"message":"nope"}', request=request)

    with patch("httpx.request", fake_request):
        try:
            store.list_portfolio()
        except SupabaseHttpError as e:
            assert e.status == 401
            assert "nope" in e.body
        else:
            raise AssertionError("Expected SupabaseHttpError")


def test_create_event_posts_and_parses_representation() -> None:
    store = SupabaseStore(
        supabase_url="https://example.supabase.co", service_role_key="k"
    )
    captured = {}

    ts = datetime(2026, 3, 22, 0, 0, 0, tzinfo=UTC)
    response = json.dumps(
        [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "ticker": "AAPL",
                "type": EventType.PRICE_MOVE.value,
                "severity": 1,
                "payload": {"pct_change": 3.2},
                "event_time": ts.isoformat(),
            }
        ]
    ).encode("utf-8")

    def fake_request(method, url, params=None, headers=None, content=None, **kwargs):
        captured["url"] = str(httpx.URL(url, params=params or {}))
        captured["headers"] = _lower_headers(dict(headers or {}))
        captured["method"] = method
        captured["data"] = content
        request = httpx.Request(method, captured["url"])
        return httpx.Response(200, content=response, request=request)

    with patch("httpx.request", fake_request):
        evt = store.create_event(
            ticker="aapl",
            type=EventType.PRICE_MOVE,
            severity=1,
            payload={"pct_change": 3.2},
            event_time=ts,
        )

    assert captured["method"] == "POST"
    assert "rest/v1/events" in captured["url"]
    assert captured["headers"]["prefer"] == "return=representation"
    assert evt.ticker == "AAPL"
    assert evt.type is EventType.PRICE_MOVE
    assert evt.payload["pct_change"] == 3.2


def test_try_mark_notification_sent_returns_false_on_conflict() -> None:
    store = SupabaseStore(
        supabase_url="https://example.supabase.co", service_role_key="k"
    )

    def fake_request(method, url, params=None, **kwargs):
        full_url = str(httpx.URL(url, params=params or {}))
        request = httpx.Request(method, full_url)
        return httpx.Response(409, content=b'{"message":"duplicate"}', request=request)

    with patch("httpx.request", fake_request):
        ok = store.try_mark_notification_sent(
            event_id=UUID("11111111-1111-1111-1111-111111111111"),
            channel="telegram",
            dedupe_key="PRICE_MOVE:AAPL:2026-03-22:UP:2",
        )

    assert ok is False
