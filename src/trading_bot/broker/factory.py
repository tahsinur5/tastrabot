from __future__ import annotations

from trading_bot.broker.client import BrokerClient
from trading_bot.broker.ibkr import IbkrBrokerClient, IbkrConfig
from trading_bot.broker.noop import NoopBrokerClient
from trading_bot.config import Settings, is_local_mode


def create_broker(settings: Settings) -> BrokerClient:
    if not is_local_mode(settings):
        return NoopBrokerClient()

    config = IbkrConfig(
        host=settings.ibkr_host,
        port=settings.ibkr_port,
        client_id=settings.ibkr_client_id,
        trading_mode=settings.ibkr_trading_mode,
    )
    return IbkrBrokerClient(config)

