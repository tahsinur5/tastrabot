from __future__ import annotations

from datetime import UTC, datetime

from trading_bot.adapters.prices.models import Quote
from trading_bot.adapters.storage.store import EventType, StockSettingsRow
from trading_bot.services.price_poller import _build_dedupe_key, _decide_alert


def _quote(*, price: float, prev_close: float) -> Quote:
    return Quote(
        symbol="AAPL",
        price=price,
        prev_close=prev_close,
        asof=datetime(2026, 3, 27, 14, 30, 0, tzinfo=UTC),
        provider="yahoo",
    )


def test_decide_alert_returns_none_when_move_below_threshold() -> None:
    decision = _decide_alert(
        quote=_quote(price=101.0, prev_close=100.0),
        stock_settings=None,
        default_alert_pct=2.0,
        default_huge_move_pct=5.0,
        default_cooldown_minutes=60,
    )
    assert decision is None


def test_decide_alert_returns_price_move() -> None:
    decision = _decide_alert(
        quote=_quote(price=103.0, prev_close=100.0),
        stock_settings=None,
        default_alert_pct=2.0,
        default_huge_move_pct=5.0,
        default_cooldown_minutes=60,
    )
    assert decision is not None
    assert decision.event_type is EventType.PRICE_MOVE
    assert decision.direction == "UP"
    assert decision.threshold_pct == 2.0


def test_decide_alert_returns_outlier_move() -> None:
    decision = _decide_alert(
        quote=_quote(price=94.0, prev_close=100.0),
        stock_settings=None,
        default_alert_pct=2.0,
        default_huge_move_pct=5.0,
        default_cooldown_minutes=60,
    )
    assert decision is not None
    assert decision.event_type is EventType.OUTLIER_MOVE
    assert decision.direction == "DOWN"
    assert decision.threshold_pct == 5.0


def test_decide_alert_respects_stock_mute() -> None:
    settings = StockSettingsRow(
        ticker="AAPL",
        state="WATCH",
        alert_pct=1.0,
        huge_move_pct=3.0,
        cooldown_minutes=30,
        news_level="NORMAL",
        muted=True,
    )
    decision = _decide_alert(
        quote=_quote(price=105.0, prev_close=100.0),
        stock_settings=settings,
        default_alert_pct=2.0,
        default_huge_move_pct=5.0,
        default_cooldown_minutes=60,
    )
    assert decision is None


def test_build_dedupe_key_uses_cooldown_bucket() -> None:
    asof = datetime(2026, 3, 27, 14, 30, 0, tzinfo=UTC)
    key = _build_dedupe_key(
        symbol="AAPL",
        event_type=EventType.PRICE_MOVE,
        direction="UP",
        asof=asof,
        cooldown_minutes=60,
    )
    assert key.startswith("PRICE_MOVE:AAPL:UP:")


def test_build_dedupe_key_no_cooldown_uses_timestamp() -> None:
    asof = datetime(2026, 3, 27, 14, 30, 0, tzinfo=UTC)
    key = _build_dedupe_key(
        symbol="AAPL",
        event_type=EventType.PRICE_MOVE,
        direction="UP",
        asof=asof,
        cooldown_minutes=0,
    )
    assert key == f"PRICE_MOVE:AAPL:UP:{asof.isoformat()}"
