from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from .auth import FirebaseAuth
from .models import SUGroup, SUMember, SUTransaction, generate_push_id

BASE_URL = "https://settle-up-live.firebaseio.com"


class SettleUpError(Exception):
    pass


class AuthError(SettleUpError):
    pass


class NotFoundError(SettleUpError):
    pass


@dataclass
class SettleUpClient:
    uid: str
    auth: FirebaseAuth
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=20.0)

    async def _get(self, path: str) -> Any:
        token = await self.auth.get_id_token()
        resp = await self._client.get(f"{path}.json", params={"auth": token})
        self._check(resp)
        return resp.json()

    async def _put(self, path: str, data: dict) -> Any:
        token = await self.auth.get_id_token()
        resp = await self._client.put(f"{path}.json", params={"auth": token}, json=data)
        self._check(resp)
        return resp.json()

    async def _patch(self, path: str, data: dict) -> Any:
        token = await self.auth.get_id_token()
        resp = await self._client.patch(f"{path}.json", params={"auth": token}, json=data)
        self._check(resp)
        return resp.json()

    async def _delete(self, path: str) -> None:
        token = await self.auth.get_id_token()
        resp = await self._client.delete(f"{path}.json", params={"auth": token})
        self._check(resp)

    def _check(self, resp: httpx.Response) -> None:
        if resp.status_code == 401:
            raise AuthError("Firebase auth failed — refresh token may be expired.")
        if resp.status_code == 404:
            raise NotFoundError(f"Not found: {resp.url}")
        if resp.status_code >= 400:
            raise SettleUpError(f"API error {resp.status_code}: {resp.text[:200]}")

    async def get_groups(self) -> list[SUGroup]:
        data = await self._get(f"/userGroups/{self.uid}")
        if not data:
            return []
        groups = []
        for group_id in data.keys():
            try:
                gdata = await self._get(f"/groups/{group_id}")
                if gdata:
                    groups.append(SUGroup.from_api(group_id, gdata))
            except SettleUpError:
                continue
        return groups

    async def get_members(self, group_id: str) -> dict[str, SUMember]:
        data = await self._get(f"/members/{group_id}")
        if not data:
            return {}
        return {mid: SUMember.from_api(mid, mdata) for mid, mdata in data.items()}

    async def get_transactions(self, group_id: str) -> list[SUTransaction]:
        data = await self._get(f"/transactions/{group_id}")
        if not data:
            return []
        txns = [
            SUTransaction.from_api(tid, tdata)
            for tid, tdata in data.items()
            if isinstance(tdata, dict)
        ]
        txns.sort(key=lambda t: t.date_time or __import__("datetime").datetime.min, reverse=True)
        return txns

    async def create_transaction(self, group_id: str, tx: SUTransaction) -> SUTransaction:
        push_id = generate_push_id()
        tx.id = push_id
        await self._put(f"/transactions/{group_id}/{push_id}", tx.to_api())
        await self._recalculate_debts(group_id)
        return tx

    async def update_transaction(self, group_id: str, tx: SUTransaction) -> SUTransaction:
        await self._patch(f"/transactions/{group_id}/{tx.id}", tx.to_api())
        await self._recalculate_debts(group_id)
        return tx

    async def delete_transaction(self, group_id: str, tx_id: str) -> None:
        await self._delete(f"/transactions/{group_id}/{tx_id}")
        await self._recalculate_debts(group_id)

    async def _recalculate_debts(self, group_id: str) -> None:
        """Trigger server-side debt recalculation after any transaction change."""
        try:
            token = await self.auth.get_id_token()
            push_id = generate_push_id()
            await self._client.put(
                f"/serverTasks/calculateGroupsDebts/{push_id}.json",
                params={"auth": token},
                json={"request": {"groupId": group_id}},
            )
        except Exception:
            pass  # Non-critical — debts will recalculate eventually

    async def close(self) -> None:
        await self._client.aclose()
