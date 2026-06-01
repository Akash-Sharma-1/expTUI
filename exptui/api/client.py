from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from .models import Expense, Friend, Group, User


class SplitwiseError(Exception):
    pass


class AuthError(SplitwiseError):
    pass


class NotFoundError(SplitwiseError):
    pass


class RateLimitError(SplitwiseError):
    pass


class ServerError(SplitwiseError):
    pass


BASE_URL = "https://secure.splitwise.com/api/v3.0"


@dataclass
class SplitwiseClient:
    api_key: str
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            },
            timeout=20.0,
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise SplitwiseError(f"Request timed out: {exc}") from exc
        except httpx.NetworkError as exc:
            raise SplitwiseError(f"Network error: {exc}") from exc

        if response.status_code == 401:
            raise AuthError("Invalid API key or unauthorized.")
        if response.status_code == 404:
            raise NotFoundError(f"Resource not found: {path}")
        if response.status_code == 429:
            raise RateLimitError("Rate limited by Splitwise API. Wait before retrying.")
        if response.status_code >= 500:
            raise ServerError(f"Splitwise server error ({response.status_code}).")
        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise SplitwiseError(f"API error {response.status_code}: {detail}")

        return response.json()

    async def get_current_user(self) -> User:
        data = await self._request("GET", "/get_current_user")
        return User.from_api(data.get("current_user") or data["user"])

    async def get_friends(self) -> list[Friend]:
        data = await self._request("GET", "/get_friends")
        return [Friend.from_api(f) for f in data.get("friends", [])]

    async def get_groups(self) -> list[Group]:
        data = await self._request("GET", "/get_groups")
        return [Group.from_api(g) for g in data.get("groups", [])]

    async def get_expenses(
        self,
        limit: int = 50,
        offset: int = 0,
        group_id: Optional[int] = None,
        friend_id: Optional[int] = None,
        visible: bool = True,
    ) -> list[Expense]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if group_id is not None:
            params["group_id"] = group_id
        if friend_id is not None:
            params["friend_id"] = friend_id
        data = await self._request("GET", "/get_expenses", params=params)
        expenses = [Expense.from_api(e) for e in data.get("expenses", [])]
        if visible:
            expenses = [e for e in expenses if not e.is_deleted and not e.payment]
        return expenses

    async def get_expense(self, expense_id: int) -> Expense:
        data = await self._request("GET", f"/get_expense/{expense_id}")
        return Expense.from_api(data["expense"])

    async def create_expense(self, payload: dict) -> Expense:
        data = await self._request("POST", "/create_expense", data=payload)
        expenses = data.get("expenses", [])
        if not expenses:
            raise SplitwiseError("No expense returned from create.")
        return Expense.from_api(expenses[0])

    async def update_expense(self, expense_id: int, payload: dict) -> Expense:
        data = await self._request("POST", f"/update_expense/{expense_id}", data=payload)
        expenses = data.get("expenses", [])
        if not expenses:
            raise SplitwiseError("No expense returned from update.")
        return Expense.from_api(expenses[0])

    async def delete_expense(self, expense_id: int) -> bool:
        data = await self._request("POST", f"/delete_expense/{expense_id}")
        return data.get("success", False)

    async def close(self) -> None:
        await self._client.aclose()
