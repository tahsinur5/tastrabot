from __future__ import annotations

from typing import Protocol

from trading_bot.adapters.prices.models import Quote


class PriceProvider(Protocol):
    name: str

    def get_quotes(self, symbols: list[str]) -> list[Quote]: ...
