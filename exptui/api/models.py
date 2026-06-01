from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:19], fmt[:len(fmt)])
        except ValueError:
            continue
    return None


@dataclass
class User:
    id: int
    first_name: str
    last_name: str
    email: str

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @classmethod
    def from_api(cls, data: dict) -> "User":
        return cls(
            id=data["id"],
            first_name=data.get("first_name") or "",
            last_name=data.get("last_name") or "",
            email=data.get("email") or "",
        )


@dataclass
class Friend:
    id: int
    first_name: str
    last_name: str
    email: str
    balance: list[dict] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @classmethod
    def from_api(cls, data: dict) -> "Friend":
        return cls(
            id=data["id"],
            first_name=data.get("first_name") or "",
            last_name=data.get("last_name") or "",
            email=data.get("email") or "",
            balance=data.get("balance") or [],
        )


@dataclass
class Group:
    id: int
    name: str

    @classmethod
    def from_api(cls, data: dict) -> "Group":
        return cls(id=data["id"], name=data.get("name") or "")


@dataclass
class Split:
    user_id: int
    first_name: str
    last_name: str
    paid_share: str
    owed_share: str

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @classmethod
    def from_api(cls, data: dict) -> "Split":
        user = data.get("user") or {}
        return cls(
            user_id=data.get("user_id") or user.get("id", 0),
            first_name=user.get("first_name") or "",
            last_name=user.get("last_name") or "",
            paid_share=data.get("paid_share") or "0.0",
            owed_share=data.get("owed_share") or "0.0",
        )


@dataclass
class Expense:
    id: int
    description: str
    cost: str
    currency_code: str
    date: Optional[datetime]
    created_by: Optional[User]
    users: list[Split] = field(default_factory=list)
    group_id: Optional[int] = None
    deleted_at: Optional[datetime] = None
    payment: bool = False

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def display_date(self) -> str:
        if self.date:
            return self.date.strftime("%Y-%m-%d")
        return ""

    @property
    def cost_float(self) -> float:
        try:
            return float(self.cost)
        except (ValueError, TypeError):
            return 0.0

    @classmethod
    def from_api(cls, data: dict) -> "Expense":
        created_by_data = data.get("created_by")
        users_data = data.get("users") or []
        return cls(
            id=data["id"],
            description=data.get("description") or "",
            cost=data.get("cost") or "0.0",
            currency_code=data.get("currency_code") or "USD",
            date=_parse_dt(data.get("date")),
            created_by=User.from_api(created_by_data) if created_by_data else None,
            users=[Split.from_api(u) for u in users_data],
            group_id=data.get("group_id"),
            deleted_at=_parse_dt(data.get("deleted_at")),
            payment=bool(data.get("payment")),
        )
