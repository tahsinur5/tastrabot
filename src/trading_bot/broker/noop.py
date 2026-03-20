from __future__ import annotations

from trading_bot.broker.client import BrokerClient, OpenOrder, Position


class NoopBrokerClient(BrokerClient):
    def list_positions(self) -> list[Position]:
        return []

    def list_open_orders(self) -> list[OpenOrder]:
        return []

