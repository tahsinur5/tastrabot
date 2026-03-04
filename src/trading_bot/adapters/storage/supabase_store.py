from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict
from typing import Any

from .store import PortfolioRow, StockSettingsRow, Store, WishlistRow


class SupabaseStore(Store):
    def __init__(self, *, supabase_url: str, service_role_key: str) -> None:
        self._base_url = supabase_url.rstrip("/") + "/"
        self._service_role_key = service_role_key

    def list_portfolio(self) -> list[PortfolioRow]:
        rows = self._get_json(
            "rest/v1/portfolio",
            {
                "select": "ticker,quantity,enabled",
                "enabled": "eq.true",
                "order": "ticker.asc",
            },
        )
        return [
            PortfolioRow(
                ticker=str(r["ticker"]).upper(),
                quantity=float(r.get("quantity") or 0),
                enabled=bool(r.get("enabled", True)),
            )
            for r in rows
        ]

    def list_wishlist(self) -> list[WishlistRow]:
        rows = self._get_json(
            "rest/v1/wishlist",
            {
                "select": "ticker,target_price,enabled",
                "enabled": "eq.true",
                "order": "ticker.asc",
            },
        )
        out: list[WishlistRow] = []
        for r in rows:
            target = r.get("target_price", None)
            out.append(
                WishlistRow(
                    ticker=str(r["ticker"]).upper(),
                    target_price=None if target in (None, "") else float(target),
                    enabled=bool(r.get("enabled", True)),
                )
            )
        return out

    def get_stock_settings(self, ticker: str) -> StockSettingsRow | None:
        t = ticker.upper()
        rows = self._get_json(
            "rest/v1/stock_settings",
            {"select": "*", "ticker": f"eq.{t}", "limit": "1"},
        )
        if not rows:
            return None
        return _row_to_stock_settings(rows[0])

    def upsert_stock_settings(
        self,
        ticker: str,
        *,
        state: str | None = None,
        alert_pct: float | None = None,
        huge_move_pct: float | None = None,
        cooldown_minutes: int | None = None,
        news_level: str | None = None,
        muted: bool | None = None,
    ) -> None:
        t = ticker.upper()
        payload: dict[str, Any] = {"ticker": t}
        if state is not None:
            payload["state"] = state
        if alert_pct is not None:
            payload["alert_pct"] = alert_pct
        if huge_move_pct is not None:
            payload["huge_move_pct"] = huge_move_pct
        if cooldown_minutes is not None:
            payload["cooldown_minutes"] = cooldown_minutes
        if news_level is not None:
            payload["news_level"] = news_level
        if muted is not None:
            payload["muted"] = muted

        self._post_json(
            "rest/v1/stock_settings",
            payload,
            query={"on_conflict": "ticker"},
            headers={
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
        )

    def _get_json(self, path: str, query: dict[str, str]) -> list[dict[str, Any]]:
        url = self._build_url(path, query)
        req = urllib.request.Request(url, method="GET", headers=self._headers())
        data = self._request(req)
        decoded = json.loads(data.decode("utf-8")) if data else []
        if not isinstance(decoded, list):
            raise TypeError("Unexpected response type from Supabase (expected list)")
        return decoded

    def _post_json(
        self,
        path: str,
        body: dict[str, Any],
        *,
        query: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        url = self._build_url(path, query or {})
        request_headers = self._headers()
        request_headers["Content-Type"] = "application/json"
        if headers:
            request_headers.update(headers)
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers=request_headers,
        )
        self._request(req)

    def _build_url(self, path: str, query: dict[str, str]) -> str:
        base = urllib.parse.urljoin(self._base_url, path)
        if not query:
            return base
        return base + "?" + urllib.parse.urlencode(query)

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self._service_role_key,
            "Authorization": f"Bearer {self._service_role_key}",
        }

    def _request(self, req: urllib.request.Request) -> bytes:
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Supabase HTTP {e.code}: {body}") from e


def _row_to_stock_settings(r: dict[str, Any]) -> StockSettingsRow:
    return StockSettingsRow(
        ticker=str(r["ticker"]).upper(),
        state=str(r.get("state") or "WATCH"),
        alert_pct=float(r.get("alert_pct") or 2.0),
        huge_move_pct=float(r.get("huge_move_pct") or 5.0),
        cooldown_minutes=int(r.get("cooldown_minutes") or 60),
        news_level=str(r.get("news_level") or "NORMAL"),
        muted=bool(r.get("muted") or False),
    )

