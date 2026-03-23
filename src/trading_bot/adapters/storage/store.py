from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class PortfolioRow:
    ticker: str
    quantity: float
    enabled: bool


@dataclass(frozen=True)
class WishlistRow:
    ticker: str
    target_price: float | None
    enabled: bool


@dataclass(frozen=True)
class StockSettingsRow:
    ticker: str
    state: str
    alert_pct: float
    huge_move_pct: float
    cooldown_minutes: int
    news_level: str
    muted: bool


class EventType(StrEnum):
    PRICE_MOVE = "PRICE_MOVE"
    OUTLIER_MOVE = "OUTLIER_MOVE"
    NEWS_EVENT = "NEWS_EVENT"
    EARNINGS = "EARNINGS"
    FILING = "FILING"
    VOLUME_SPIKE = "VOLUME_SPIKE"


@dataclass(frozen=True)
class Event:
    id: UUID
    ticker: str
    type: EventType
    severity: int
    payload: dict
    event_time: datetime


class Store(Protocol):
    def list_portfolio(self) -> list[PortfolioRow]: ...

    def list_wishlist(self) -> list[WishlistRow]: ...

    def get_stock_settings(self, ticker: str) -> StockSettingsRow | None: ...

    def upsert_stock_settings(
        self,
        ticker: str,
        *,
        state: str | None = None,
        alert_pct: float | None = None,
        huge_move_pct: float | None = None,
        cooldown_minutes: int | None = None,
        news_level: str | None = None,
        muted: bool | None = None,
    ) -> None: ...

    def create_event(
        self,
        *,
        ticker: str,
        type: EventType,
        severity: int,
        payload: dict,
        event_time: datetime | None = None,
    ) -> Event: ...

    def try_mark_notification_sent(
        self,
        *,
        event_id: UUID,
        channel: str,
        dedupe_key: str,
    ) -> bool: ...
