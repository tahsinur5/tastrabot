from __future__ import annotations

import argparse
import logging

from .config import Settings
from .observability.health import HealthState
from .observability.logging import configure_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trading_bot")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate settings and exit (no external calls).",
    )
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    configure_logging(settings.log_level)

    logger = logging.getLogger("trading_bot")
    health = HealthState()
    logger.info(
        "startup",
        extra={
            "tz": settings.tz,
            "poll_interval_seconds": settings.poll_interval_seconds,
        },
    )

    if args.check:
        logger.info("check_ok", extra={"degraded_mode": health.degraded_mode})
        return 0

    logger.info("not_implemented_yet", extra={"next": "Step 3+ adapters/jobs"})
    return 0

