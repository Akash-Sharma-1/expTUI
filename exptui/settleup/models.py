from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

PUSH_CHARS = "-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz"


def generate_push_id() -> str:
    now = int(time.time() * 1000)
    result = [""] * 20
    for i in range(7, -1, -1):
        result[i] = PUSH_CHARS[now % 64]
        now //= 64
    for i in range(8, 20):
        result[i] = random.choice(PUSH_CHARS)
    return "".join(result)


def _parse_dt(value) -> Optional[datetime]:
    if value is None:
        return None
    # Unix ms timestamp (actual format)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    # ISO string fallback
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            pass
    return None


@dataclass
class SUMember:
    id: str
    name: str
    active: bool = True
    photo_url: str = ""

    @classmethod
    def from_api(cls, id: str, data: dict) -> "SUMember":
        return cls(
            id=id,
            name=data.get("name") or "Unknown",
            active=data.get("active", True),
            photo_url=data.get("photoUrl") or "",
        )


@dataclass
class SUGroup:
    id: str
    name: str
    currency: str = "INR"

    @classmethod
    def from_api(cls, id: str, data: dict) -> "SUGroup":
        return cls(
            id=id,
            name=data.get("name") or id,
            currency=data.get("convertedToCurrency") or "INR",
        )


@dataclass
class SUTransaction:
    """
    Actual Firebase structure:
      whoPaid:  [{"memberId": "...", "weight": "31000"}]   (weight = amount paid)
      items:    [{"amount": "31000", "forWhom": [{"memberId": "...", "weight": "1"}]}]
      dateTime: unix ms integer
    """
    id: str
    purpose: str
    currency_code: str
    date_time: Optional[datetime]
    tx_type: str
    who_paid: list[dict]    # [{"memberId": str, "weight": str}]
    items: list[dict]       # [{"amount": str, "forWhom": [{"memberId": str, "weight": str}]}]
    category: str = ""
    receipt_url: str = ""
    exchange_rates: dict = field(default_factory=dict)

    @property
    def total_amount(self) -> float:
        # Amount lives in items[].amount; whoPaid[].weight is a ratio (often "1")
        try:
            if self.items:
                return sum(float(item.get("amount", 0)) for item in self.items)
            # Fallback for old format where weight was the actual amount
            return sum(float(p.get("weight", 0)) for p in self.who_paid)
        except (ValueError, TypeError):
            return 0.0

    @property
    def payer_id(self) -> str:
        return self.who_paid[0].get("memberId", "") if self.who_paid else ""

    @property
    def display_date(self) -> str:
        return self.date_time.strftime("%Y-%m-%d") if self.date_time else ""

    def for_whom_ids(self) -> list[str]:
        if self.items:
            return [fw["memberId"] for fw in (self.items[0].get("forWhom") or [])]
        return []

    def to_api(self) -> dict:
        dt_ms = int(self.date_time.timestamp() * 1000) if self.date_time else int(time.time() * 1000)
        return {
            "purpose": self.purpose,
            "currencyCode": self.currency_code,
            "dateTime": dt_ms,
            "type": self.tx_type,
            "whoPaid": self.who_paid,
            "items": self.items,
            "exchangeRates": self.exchange_rates or {self.currency_code: "1"},
            "fixedExchangeRate": False,
        }

    @classmethod
    def from_api(cls, id: str, data: dict) -> "SUTransaction":
        who_paid_raw = data.get("whoPaid") or []
        # normalise: might be list or (rarely) dict
        if isinstance(who_paid_raw, dict):
            who_paid = [{"memberId": k, "weight": str(v)} for k, v in who_paid_raw.items()]
        else:
            who_paid = [{"memberId": e.get("memberId", ""), "weight": str(e.get("weight", "0"))}
                        for e in who_paid_raw if isinstance(e, dict)]

        items = data.get("items") or []
        return cls(
            id=id,
            purpose=data.get("purpose") or "",
            currency_code=data.get("currencyCode") or "INR",
            date_time=_parse_dt(data.get("dateTime")),
            tx_type=data.get("type") or "expense",
            who_paid=who_paid,
            items=items,
            category=data.get("category") or "",
            receipt_url=data.get("receiptUrl") or "",
            exchange_rates=data.get("exchangeRates") or {},
        )
