from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: float
    avg_cost: float | None = None


@dataclass(frozen=True)
class OpenOrder:
    symbol: str
    order_id: int
    side: str | None = None
    quantity: float | None = None
    limit_price: float | None = None


class BrokerClient(Protocol):
    def list_positions(self) -> list[Position]: ...

    def list_open_orders(self) -> list[OpenOrder]: ...
