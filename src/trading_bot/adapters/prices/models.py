from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    prev_close: float | None
    asof: datetime
    provider: str

    @property
    def pct_change_from_prev_close(self) -> float | None:
        if self.prev_close is None or self.prev_close == 0:
            return None
        return (self.price - self.prev_close) / self.prev_close * 100.0
