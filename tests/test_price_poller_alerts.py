from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from trading_bot.adapters.prices.models import Quote
from trading_bot.adapters.storage.store import Event, EventType, StockSettingsRow
from trading_bot.config import Settings
from trading_bot.services.price_poller import (
    _build_dedupe_key,
    _decide_alert,
    _is_quiet_hours,
    _process_quote_alerts,
)


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


def test_decide_alert_buy_state_only_allows_down_moves() -> None:
    settings = StockSettingsRow(
        ticker="AAPL",
        state="BUY",
        alert_pct=2.0,
        huge_move_pct=5.0,
        cooldown_minutes=60,
        news_level="NORMAL",
        muted=False,
    )
    up_move = _decide_alert(
        quote=_quote(price=103.0, prev_close=100.0),
        stock_settings=settings,
        default_alert_pct=2.0,
        default_huge_move_pct=5.0,
        default_cooldown_minutes=60,
    )
    down_move = _decide_alert(
        quote=_quote(price=97.0, prev_close=100.0),
        stock_settings=settings,
        default_alert_pct=2.0,
        default_huge_move_pct=5.0,
        default_cooldown_minutes=60,
    )
    assert up_move is None
    assert down_move is not None
    assert down_move.direction == "DOWN"


def test_decide_alert_sell_state_only_allows_up_moves() -> None:
    settings = StockSettingsRow(
        ticker="AAPL",
        state="SELL",
        alert_pct=2.0,
        huge_move_pct=5.0,
        cooldown_minutes=60,
        news_level="NORMAL",
        muted=False,
    )
    down_move = _decide_alert(
        quote=_quote(price=97.0, prev_close=100.0),
        stock_settings=settings,
        default_alert_pct=2.0,
        default_huge_move_pct=5.0,
        default_cooldown_minutes=60,
    )
    up_move = _decide_alert(
        quote=_quote(price=103.0, prev_close=100.0),
        stock_settings=settings,
        default_alert_pct=2.0,
        default_huge_move_pct=5.0,
        default_cooldown_minutes=60,
    )
    assert down_move is None
    assert up_move is not None
    assert up_move.direction == "UP"


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


def test_is_quiet_hours_handles_overnight_window() -> None:
    assert _is_quiet_hours(
        now=datetime.fromisoformat("2026-03-27T03:30:00+00:00"),
        tz="America/New_York",
        start_hhmm="22:00",
        end_hhmm="07:00",
    )
    assert not _is_quiet_hours(
        now=datetime.fromisoformat("2026-03-27T13:00:00+00:00"),
        tz="America/New_York",
        start_hhmm="22:00",
        end_hhmm="07:00",
    )


def test_is_quiet_hours_handles_same_day_window() -> None:
    assert _is_quiet_hours(
        now=datetime.fromisoformat("2026-03-27T16:30:00+00:00"),
        tz="America/New_York",
        start_hhmm="12:00",
        end_hhmm="13:00",
    )
    assert not _is_quiet_hours(
        now=datetime.fromisoformat("2026-03-27T18:01:00+00:00"),
        tz="America/New_York",
        start_hhmm="12:00",
        end_hhmm="13:00",
    )


class _Store:
    def __init__(self) -> None:
        self.events: list[Event] = []
        self.mark_calls = 0

    def get_stock_settings(self, ticker: str):
        return None

    def create_event(self, *, ticker, type, severity, payload, event_time=None):
        event = Event(
            id=uuid4(),
            ticker=ticker,
            type=type,
            severity=severity,
            payload=payload,
            event_time=event_time or datetime.now(tz=UTC),
        )
        self.events.append(event)
        return event

    def try_mark_notification_sent(self, *, event_id, channel, dedupe_key):
        self.mark_calls += 1
        return True


def test_process_quote_alerts_suppresses_notifications_during_quiet_hours() -> None:
    store = _Store()
    sent_messages: list[str] = []
    settings = Settings(
        tz="America/New_York",
        quiet_hours_start="22:00",
        quiet_hours_end="07:00",
    )
    quote = Quote(
        symbol="AAPL",
        price=103.0,
        prev_close=100.0,
        asof=datetime.fromisoformat("2026-03-27T03:30:00+00:00"),
        provider="yahoo",
    )

    _process_quote_alerts(
        store=store,
        settings=settings,
        quotes=[quote],
        notify=sent_messages.append,
        logger=logging.getLogger("test.price_poller"),
    )

    assert len(store.events) == 1
    assert store.mark_calls == 0
    assert sent_messages == []


def test_process_quote_alerts_sends_notifications_outside_quiet_hours() -> None:
    store = _Store()
    sent_messages: list[str] = []
    settings = Settings(
        tz="America/New_York",
        quiet_hours_start="22:00",
        quiet_hours_end="07:00",
    )
    quote = Quote(
        symbol="AAPL",
        price=103.0,
        prev_close=100.0,
        asof=datetime.fromisoformat("2026-03-27T14:30:00+00:00"),
        provider="yahoo",
    )

    _process_quote_alerts(
        store=store,
        settings=settings,
        quotes=[quote],
        notify=sent_messages.append,
        logger=logging.getLogger("test.price_poller"),
    )

    assert len(store.events) == 1
    assert store.mark_calls == 1
    assert len(sent_messages) == 1
