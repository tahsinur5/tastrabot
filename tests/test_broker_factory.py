from __future__ import annotations

from trading_bot.broker.factory import create_broker
from trading_bot.broker.noop import NoopBrokerClient
from trading_bot.config import Settings


def test_create_broker_aws_mode_is_noop() -> None:
    s = Settings.from_env({"APP_MODE": "aws"})
    broker = create_broker(s)
    assert isinstance(broker, NoopBrokerClient)


def test_create_broker_local_mode_is_ibkr() -> None:
    s = Settings.from_env({"APP_MODE": "local"})
    broker = create_broker(s)
    # Avoid importing ib_insync in tests; just assert type name.
    assert broker.__class__.__name__ == "IbkrBrokerClient"

