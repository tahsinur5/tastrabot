from trading_bot.config import Settings


def test_settings_defaults() -> None:
    s = Settings.from_env({})
    assert s.tz == "America/New_York"
    assert s.poll_interval_seconds == 300


def test_settings_parses_ints() -> None:
    s = Settings.from_env({"POLL_INTERVAL_SECONDS": "123"})
    assert s.poll_interval_seconds == 123

