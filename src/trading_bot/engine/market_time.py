from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class MarketWindow:
    tz: str = "America/New_York"
    open_hhmm: str = "09:30"
    close_hhmm: str = "16:00"

    def is_regular_market_open(self, now: datetime | None = None) -> bool:
        tzn = ZoneInfo(self.tz)
        dt = (now or datetime.now(tz=tzn)).astimezone(tzn)

        # Monday=0 ... Sunday=6
        if dt.weekday() >= 5:
            return False

        open_h, open_m = _parse_hhmm(self.open_hhmm)
        close_h, close_m = _parse_hhmm(self.close_hhmm)
        minutes = dt.hour * 60 + dt.minute
        return (open_h * 60 + open_m) <= minutes <= (close_h * 60 + close_m)

    def seconds_until_next_open(self, now: datetime | None = None) -> int:
        tzn = ZoneInfo(self.tz)
        dt = (now or datetime.now(tz=tzn)).astimezone(tzn)
        next_open = self.next_regular_market_open(now=dt)
        delta = next_open - dt
        # Return at least 1 second to avoid accidental tight loops.
        return max(1, int(delta.total_seconds()))

    def next_regular_market_open(self, now: datetime | None = None) -> datetime:
        tzn = ZoneInfo(self.tz)
        dt = (now or datetime.now(tz=tzn)).astimezone(tzn)
        open_h, open_m = _parse_hhmm(self.open_hhmm)
        close_h, close_m = _parse_hhmm(self.close_hhmm)

        candidate = dt.replace(
            hour=open_h,
            minute=open_m,
            second=0,
            microsecond=0,
        )
        close_dt = dt.replace(
            hour=close_h,
            minute=close_m,
            second=0,
            microsecond=0,
        )

        if dt.weekday() < 5:
            if dt < candidate:
                return candidate
            if dt <= close_dt:
                return dt

        next_day = dt + timedelta(days=1)
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
        return next_day.replace(hour=open_h, minute=open_m, second=0, microsecond=0)


def _parse_hhmm(value: str) -> tuple[int, int]:
    h, m = value.split(":")
    return int(h), int(m)
