from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock


@dataclass
class HealthState:
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)
    last_poll_at: datetime | None = None
    degraded_mode: bool = False
    last_price_provider: str | None = None

    def mark_poll(self, *, provider: str, degraded: bool) -> None:
        now = datetime.now(tz=timezone.utc)
        with self._lock:
            self.last_poll_at = now
            self.last_price_provider = provider
            self.degraded_mode = degraded

