from __future__ import annotations

import os
from dataclasses import dataclass


def _to_int(value: str | None, *, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    app_mode: str = "aws"  # "aws" | "local"
    tz: str = "America/New_York"
    log_level: str = "INFO"

    poll_interval_seconds: int = 300
    degraded_poll_interval_seconds: int = 900

    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"

    default_alert_pct: float = 2.0
    default_huge_move_pct: float = 5.0
    default_cooldown_minutes: int = 60

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    supabase_url: str | None = None
    supabase_secret_key: str | None = None

    finnhub_api_key: str | None = None
    marketaux_api_key: str | None = None

    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 4001
    ibkr_client_id: int = 1
    ibkr_trading_mode: str = "paper"  # "paper" | "live"

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> Settings:
        env = os.environ if environ is None else environ
        return cls(
            app_mode=(env.get("APP_MODE", cls.app_mode) or cls.app_mode).lower(),
            tz=env.get("TZ", cls.tz),
            log_level=env.get("LOG_LEVEL", cls.log_level),
            poll_interval_seconds=_to_int(
                env.get("POLL_INTERVAL_SECONDS"), default=cls.poll_interval_seconds
            ),
            degraded_poll_interval_seconds=_to_int(
                env.get("DEGRADED_POLL_INTERVAL_SECONDS"),
                default=cls.degraded_poll_interval_seconds,
            ),
            quiet_hours_start=env.get("QUIET_HOURS_START", cls.quiet_hours_start),
            quiet_hours_end=env.get("QUIET_HOURS_END", cls.quiet_hours_end),
            default_alert_pct=float(
                env.get("DEFAULT_ALERT_PCT", cls.default_alert_pct)
            ),
            default_huge_move_pct=float(
                env.get("DEFAULT_HUGE_MOVE_PCT", cls.default_huge_move_pct)
            ),
            default_cooldown_minutes=_to_int(
                env.get("DEFAULT_COOLDOWN_MINUTES"),
                default=cls.default_cooldown_minutes,
            ),
            telegram_bot_token=env.get("TELEGRAM_BOT_TOKEN") or None,
            telegram_chat_id=env.get("TELEGRAM_CHAT_ID") or None,
            supabase_url=env.get("SUPABASE_URL") or None,
            supabase_secret_key=(
                env.get("SUPABASE_SECRET_KEY")
                or env.get("SUPABASE_SERVICE_ROLE_KEY")
                or None
            ),
            finnhub_api_key=env.get("FINNHUB_API_KEY") or None,
            marketaux_api_key=env.get("MARKETAUX_API_KEY") or None,
            ibkr_host=env.get("IBKR_HOST", cls.ibkr_host),
            ibkr_port=_to_int(env.get("IBKR_PORT"), default=cls.ibkr_port),
            ibkr_client_id=_to_int(
                env.get("IBKR_CLIENT_ID"), default=cls.ibkr_client_id
            ),
            ibkr_trading_mode=(
                env.get("IBKR_TRADING_MODE", cls.ibkr_trading_mode)
                or cls.ibkr_trading_mode
            ).lower(),
        )

    def require(self, *names: str) -> None:
        missing: list[str] = []
        for name in names:
            if not getattr(self, name, None):
                missing.append(name)
        if missing:
            missing_env = ", ".join(_setting_to_env(n) for n in missing)
            raise ValueError(f"Missing required settings: {missing_env}")


def _setting_to_env(setting_name: str) -> str:
    mapping = {
        "app_mode": "APP_MODE",
        "telegram_bot_token": "TELEGRAM_BOT_TOKEN",
        "telegram_chat_id": "TELEGRAM_CHAT_ID",
        "supabase_url": "SUPABASE_URL",
        "supabase_secret_key": "SUPABASE_SECRET_KEY",
        "finnhub_api_key": "FINNHUB_API_KEY",
        "marketaux_api_key": "MARKETAUX_API_KEY",
        "ibkr_host": "IBKR_HOST",
        "ibkr_port": "IBKR_PORT",
        "ibkr_client_id": "IBKR_CLIENT_ID",
        "ibkr_trading_mode": "IBKR_TRADING_MODE",
    }
    return mapping.get(setting_name, setting_name.upper())


def is_local_mode(settings: Settings) -> bool:
    return settings.app_mode == "local"
