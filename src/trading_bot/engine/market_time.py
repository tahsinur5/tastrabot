from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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


def _parse_hhmm(value: str) -> tuple[int, int]:
    h, m = value.split(":")
    return int(h), int(m)
