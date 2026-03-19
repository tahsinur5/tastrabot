from __future__ import annotations

from dataclasses import dataclass

from trading_bot.adapters.storage.store import Store
from trading_bot.observability.health import HealthState


@dataclass(frozen=True)
class BotContext:
    store: Store | None
    health: HealthState
    telegram_chat_id: str


def handle_command(ctx: BotContext, text: str) -> str:
    parts = text.strip().split()
    if not parts:
        return _help_text()

    cmd = parts[0].lower()
    args = parts[1:]

    if cmd in {"/help", "help"}:
        return _help_text()
    if cmd == "/health":
        return _health_text(ctx)

    if ctx.store is None:
        return "Storage is not configured yet."

    if cmd == "/portfolio":
        return _portfolio_text(ctx)
    if cmd == "/watchlist":
        return _watchlist_text(ctx)
    if cmd == "/setstate":
        return _set_state(ctx, args)
    if cmd == "/setalert":
        return _set_alert(ctx, args)
    if cmd == "/mute":
        return _mute(ctx, args)

    return _help_text()


def _help_text() -> str:
    return "\n".join(
        [
            "Commands:",
            "/portfolio — list enabled portfolio tickers",
            "/watchlist — list enabled watchlist tickers",
            "/setstate TICKER BUY|SELL|WATCH",
            "/setalert TICKER alert_pct huge_move_pct cooldown_minutes",
            "/mute TICKER on|off",
            "/mute all on|off",
            "/health — bot status",
        ]
    )


def _health_text(ctx: BotContext) -> str:
    last = ctx.health.last_poll_at.isoformat() if ctx.health.last_poll_at else "never"
    provider = ctx.health.last_price_provider or "n/a"
    return "\n".join(
        [
            "Health:",
            f"last_poll_at: {last}",
            f"degraded_mode: {ctx.health.degraded_mode}",
            f"last_price_provider: {provider}",
        ]
    )


def _portfolio_text(ctx: BotContext) -> str:
    assert ctx.store is not None
    rows = ctx.store.list_portfolio()
    if not rows:
        return "Portfolio is empty."
    lines: list[str] = ["Portfolio:"]
    for r in rows:
        settings = ctx.store.get_stock_settings(r.ticker)
        state = settings.state if settings else "WATCH"
        muted = settings.muted if settings else False
        muted_str = " (muted)" if muted else ""
        lines.append(f"- {r.ticker}: qty={r.quantity:g}, state={state}{muted_str}")
    return "\n".join(lines)


def _watchlist_text(ctx: BotContext) -> str:
    assert ctx.store is not None
    rows = ctx.store.list_wishlist()
    if not rows:
        return "Watchlist is empty."
    lines: list[str] = ["Watchlist:"]
    for r in rows:
        tgt = f"{r.target_price:g}" if r.target_price is not None else "n/a"
        lines.append(f"- {r.ticker}: target={tgt}")
    return "\n".join(lines)


def _set_state(ctx: BotContext, args: list[str]) -> str:
    assert ctx.store is not None
    if len(args) != 2:
        return "Usage: /setstate TICKER BUY|SELL|WATCH"
    ticker = args[0].upper()
    state = args[1].upper()
    if state not in {"BUY", "SELL", "WATCH"}:
        return "State must be one of: BUY, SELL, WATCH"
    ctx.store.upsert_stock_settings(ticker, state=state)
    return f"Updated {ticker} state to {state}."


def _set_alert(ctx: BotContext, args: list[str]) -> str:
    assert ctx.store is not None
    if len(args) != 4:
        return "Usage: /setalert TICKER alert_pct huge_move_pct cooldown_minutes"
    ticker = args[0].upper()
    try:
        alert_pct = float(args[1])
        huge_move_pct = float(args[2])
        cooldown_minutes = int(args[3])
    except ValueError:
        return "Invalid numbers. Example: /setalert AAPL 2.0 5.0 60"
    if alert_pct <= 0 or huge_move_pct <= 0 or cooldown_minutes < 0:
        return "alert_pct/huge_move_pct must be > 0 and cooldown_minutes must be >= 0"
    ctx.store.upsert_stock_settings(
        ticker,
        alert_pct=alert_pct,
        huge_move_pct=huge_move_pct,
        cooldown_minutes=cooldown_minutes,
    )
    return (
        f"Updated {ticker} alerts: alert_pct={alert_pct:g}, "
        f"huge_move_pct={huge_move_pct:g}, cooldown_minutes={cooldown_minutes}"
    )


def _mute(ctx: BotContext, args: list[str]) -> str:
    assert ctx.store is not None
    if len(args) != 2:
        return "Usage: /mute TICKER on|off  (or: /mute all on|off)"
    ticker = args[0].upper()
    flag = args[1].lower()
    if flag not in {"on", "off"}:
        return "Usage: /mute TICKER on|off"
    muted = flag == "on"
    if ticker == "ALL":
        ctx.store.upsert_stock_settings("__GLOBAL__", muted=muted)
        return f"Global mute is now {'ON' if muted else 'OFF'}."
    ctx.store.upsert_stock_settings(ticker, muted=muted)
    return f"Muted {ticker} is now {'ON' if muted else 'OFF'}."
