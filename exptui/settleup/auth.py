from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
import sys

import httpx

TOKEN_URL = "https://securetoken.googleapis.com/v1/token"
CONFIG_FILE = Path.home() / ".config" / "splitwise-tui" / "config.toml"


@dataclass
class FirebaseToken:
    id_token: str
    refresh_token: str
    expires_at: float  # unix timestamp

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at - 60  # 60s buffer


@dataclass
class FirebaseAuth:
    api_key: str
    refresh_token: str
    _token: FirebaseToken | None = field(default=None, init=False, repr=False)

    async def get_id_token(self) -> str:
        if self._token is None or self._token.is_expired:
            await self._refresh()
        return self._token.id_token  # type: ignore[union-attr]

    async def _refresh(self) -> None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                TOKEN_URL,
                params={"key": self.api_key},
                headers={
                    "Referer": "https://settleup.app",
                    "Origin": "https://settleup.app",
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                },
            )
        if resp.status_code != 200:
            raise RuntimeError(f"Firebase token refresh failed: {resp.text}")

        data = resp.json()
        self._token = FirebaseToken(
            id_token=data["id_token"],
            refresh_token=data["refresh_token"],
            expires_at=time.time() + int(data.get("expires_in", 3600)),
        )
        # Persist updated refresh token so it survives session restarts
        if self._token.refresh_token != self.refresh_token:
            self.refresh_token = self._token.refresh_token
            _save_refresh_token(self.refresh_token)


def _save_refresh_token(token: str) -> None:
    if not CONFIG_FILE.exists():
        return
    try:
        content = CONFIG_FILE.read_text()
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            if line.strip().startswith("refresh_token") and "=" in line:
                new_lines.append(f'refresh_token = "{token}"')
            else:
                new_lines.append(line)
        CONFIG_FILE.write_text("\n".join(new_lines) + "\n")
    except Exception:
        pass
