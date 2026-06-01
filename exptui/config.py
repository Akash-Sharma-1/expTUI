from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

CONFIG_FILE = Path.home() / ".config" / "exp-tui" / "config.toml"


class ConfigError(Exception):
    pass


@dataclass
class Config:
    # Splitwise (optional if only using SettleUp)
    api_key: str = ""
    default_currency: str = "INR"
    page_size: int = 50
    # Settle Up (optional if only using Splitwise)
    su_firebase_api_key: str = ""
    su_refresh_token: str = ""
    su_uid: str = ""

    @property
    def has_splitwise(self) -> bool:
        return bool(self.api_key)

    @property
    def has_settleup(self) -> bool:
        return bool(self.su_firebase_api_key and self.su_refresh_token and self.su_uid)


def _load_toml() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        if sys.version_info >= (3, 11):
            import tomllib
            with open(CONFIG_FILE, "rb") as f:
                return tomllib.load(f)
        else:
            import tomli
            with open(CONFIG_FILE, "rb") as f:
                return tomli.load(f)
    except Exception:
        return {}


def load_config() -> Config:
    data = _load_toml()

    api_key = os.environ.get("SPLITWISE_API_KEY", "").strip() or str(data.get("api_key", "")).strip()
    default_currency = str(data.get("default_currency", "INR"))
    page_size = int(data.get("page_size", 50))

    su = data.get("settleup") or {}
    su_firebase_api_key = (
        os.environ.get("SETTLEUP_FIREBASE_API_KEY", "").strip()
        or str(su.get("firebase_api_key", "")).strip()
    )
    su_refresh_token = (
        os.environ.get("SETTLEUP_REFRESH_TOKEN", "").strip()
        or str(su.get("refresh_token", "")).strip()
    )
    su_uid = (
        os.environ.get("SETTLEUP_UID", "").strip()
        or str(su.get("uid", "")).strip()
    )

    config = Config(
        api_key=api_key,
        default_currency=default_currency,
        page_size=page_size,
        su_firebase_api_key=su_firebase_api_key,
        su_refresh_token=su_refresh_token,
        su_uid=su_uid,
    )

    if not config.has_splitwise and not config.has_settleup:
        raise ConfigError(
            "No credentials found. Configure at least one provider in:\n"
            f"  {CONFIG_FILE}\n\n"
            "Splitwise:\n"
            "  api_key = \"your-token\"\n\n"
            "Settle Up:\n"
            "  [settleup]\n"
            "  firebase_api_key = \"AIzaSy...\"\n"
            "  refresh_token = \"AMf-vBz...\"\n"
            "  uid = \"your-firebase-uid\"\n"
        )

    return config
