from __future__ import annotations

from trading_bot.commands.handlers import BotContext, handle_command
from trading_bot.observability.health import HealthState


class _Store:
    def list_portfolio(self):
        return []

    def list_wishlist(self):
        return []

    def get_stock_settings(self, ticker: str):
        return None

    def upsert_stock_settings(self, ticker: str, **kwargs):
        self.last = (ticker, kwargs)


def test_help_when_empty() -> None:
    ctx = BotContext(store=None, health=HealthState(), telegram_chat_id="1")
    out = handle_command(ctx, "")
    assert "/portfolio" in out


def test_setstate_requires_store() -> None:
    ctx = BotContext(store=None, health=HealthState(), telegram_chat_id="1")
    out = handle_command(ctx, "/setstate AAPL BUY")
    assert "Storage" in out


def test_setstate_updates_store() -> None:
    store = _Store()
    ctx = BotContext(store=store, health=HealthState(), telegram_chat_id="1")
    out = handle_command(ctx, "/setstate AAPL BUY")
    assert "Updated AAPL state to BUY" in out
    assert store.last[0] == "AAPL"
    assert store.last[1]["state"] == "BUY"


def test_mute_all_sets_global() -> None:
    store = _Store()
    ctx = BotContext(store=store, health=HealthState(), telegram_chat_id="1")
    out = handle_command(ctx, "/mute all on")
    assert "Global mute" in out
    assert store.last[0] == "__GLOBAL__"
    assert store.last[1]["muted"] is True
