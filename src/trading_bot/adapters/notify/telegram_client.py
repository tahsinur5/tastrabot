from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TelegramUpdate:
    update_id: int
    message: dict[str, Any]


class TelegramClient:
    def __init__(self, *, bot_token: str) -> None:
        self._bot_token = bot_token
        self._base_url = f"https://api.telegram.org/bot{bot_token}/"

    def get_updates(self, *, offset: int | None, timeout: int = 30) -> list[TelegramUpdate]:
        params: dict[str, str] = {"timeout": str(timeout)}
        if offset is not None:
            params["offset"] = str(offset)
        data = self._get_json("getUpdates", params)
        result = data.get("result", [])
        out: list[TelegramUpdate] = []
        for u in result:
            if not isinstance(u, dict):
                continue
            if "update_id" not in u or "message" not in u:
                continue
            out.append(TelegramUpdate(update_id=int(u["update_id"]), message=u["message"]))
        return out

    def send_message(self, *, chat_id: str, text: str) -> None:
        self._post_form(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": "true",
            },
        )

    def _get_json(self, method: str, params: dict[str, str]) -> dict[str, Any]:
        url = self._base_url + method
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
        decoded = json.loads(raw.decode("utf-8")) if raw else {}
        if not isinstance(decoded, dict):
            raise TypeError("Unexpected Telegram response type")
        if decoded.get("ok") is not True:
            raise RuntimeError(f"Telegram API error: {decoded}")
        return decoded

    def _post_form(self, method: str, form: dict[str, str]) -> dict[str, Any]:
        url = self._base_url + method
        data = urllib.parse.urlencode(form).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
        decoded = json.loads(raw.decode("utf-8")) if raw else {}
        if not isinstance(decoded, dict):
            raise TypeError("Unexpected Telegram response type")
        if decoded.get("ok") is not True:
            raise RuntimeError(f"Telegram API error: {decoded}")
        return decoded

