from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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

