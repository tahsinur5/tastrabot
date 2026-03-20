from __future__ import annotations

from dataclasses import dataclass

from trading_bot.broker.client import BrokerClient, OpenOrder, Position


@dataclass(frozen=True)
class IbkrConfig:
    host: str
    port: int
    client_id: int
    trading_mode: str  # "paper" | "live"


class IbkrBrokerClient(BrokerClient):
    def __init__(self, config: IbkrConfig) -> None:
        self._config = config
        self._ib = None

    def connect(self) -> None:
        # Lazy import so AWS mode has no ib_insync dependency at runtime.
        from ib_insync import IB  # type: ignore[import-not-found]

        ib = IB()
        ib.connect(self._config.host, self._config.port, clientId=self._config.client_id)
        self._ib = ib

    def list_positions(self) -> list[Position]:
        if self._ib is None:
            raise RuntimeError("IBKR client not connected. Call connect() first.")
        out: list[Position] = []
        for p in self._ib.positions():
            out.append(
                Position(
                    symbol=str(p.contract.symbol),
                    quantity=float(p.position),
                    avg_cost=float(p.avgCost) if p.avgCost is not None else None,
                )
            )
        return out

    def list_open_orders(self) -> list[OpenOrder]:
        if self._ib is None:
            raise RuntimeError("IBKR client not connected. Call connect() first.")
        out: list[OpenOrder] = []
        for t in self._ib.openTrades():
            contract = t.contract
            order = t.order
            out.append(
                OpenOrder(
                    symbol=str(contract.symbol),
                    order_id=int(order.orderId),
                    side=str(order.action) if order.action else None,
                    quantity=float(order.totalQuantity) if order.totalQuantity is not None else None,
                    limit_price=float(order.lmtPrice) if getattr(order, "lmtPrice", None) else None,
                )
            )
        return out

