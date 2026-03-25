from __future__ import annotations

from datetime import datetime

from trading_bot.engine.market_time import MarketWindow


def test_seconds_until_next_open_before_open_same_day() -> None:
    window = MarketWindow(tz="America/New_York")
    now = datetime.fromisoformat("2026-03-25T08:00:00-04:00")  # Wednesday

    seconds = window.seconds_until_next_open(now=now)

    assert seconds == 90 * 60


def test_seconds_until_next_open_after_close_friday() -> None:
    window = MarketWindow(tz="America/New_York")
    now = datetime.fromisoformat("2026-03-27T17:00:00-04:00")  # Friday

    seconds = window.seconds_until_next_open(now=now)

    assert seconds == 64 * 60 * 60 + 30 * 60


def test_seconds_until_next_open_on_weekend() -> None:
    window = MarketWindow(tz="America/New_York")
    now = datetime.fromisoformat("2026-03-28T12:00:00-04:00")  # Saturday

    seconds = window.seconds_until_next_open(now=now)

    assert seconds == 45 * 60 * 60 + 30 * 60
