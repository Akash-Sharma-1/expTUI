from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Select, Label
from textual.containers import Vertical, Horizontal
from textual import work

from ..settleup.client import SettleUpError
from ..settleup.models import SUGroup, SUMember, SUTransaction
from ..widgets.search_bar import SearchBar
from ..widgets.status_bar import StatusBar
from .confirm_delete import ConfirmDeleteScreen
from .settleup_add import SettleUpAddScreen
from .settleup_edit import SettleUpEditScreen


class SettleUpMainScreen(Screen):
    BINDINGS = [
        ("a", "add_transaction", "Add"),
        ("e", "edit_transaction", "Edit"),
        ("d", "delete_transaction", "Delete"),
        ("slash", "focus_search", "Search"),
        ("r", "refresh", "Refresh"),
        ("j", "move_down", "Down"),
        ("k", "move_up", "Up"),
        ("q", "quit", "Quit"),
        ("escape", "clear_search", "Clear"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._groups: list[SUGroup] = []
        self._current_group: SUGroup | None = None
        self._members: dict[str, SUMember] = {}
        self._transactions: list[SUTransaction] = []
        self._search_query: str = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="main-layout"):
            with Horizontal(id="group-row"):
                yield Label("Group:", id="group-label")
                yield Select([], id="group-select", prompt="Loading groups...")
            yield SearchBar(id="search-bar")
            yield DataTable(id="tx-table")
        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#tx-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_column("Date", width=12)
        table.add_column("Purpose", width=38)
        table.add_column("Amount", width=10)
        table.add_column("Currency", width=8)
        table.add_column("Paid by", width=16)
        self._load_groups()

    @work(exclusive=True)
    async def _load_groups(self) -> None:
        status = self.query_one(StatusBar)
        status.set_loading(True)
        client = self.app.su_client  # type: ignore[attr-defined]
        try:
            self._groups = await client.get_groups()
            sel = self.query_one("#group-select", Select)
            options = [(g.name, g.id) for g in self._groups]
            sel.set_options(options)
            if self._groups:
                self._current_group = self._groups[0]
                sel.value = self._groups[0].id
                await self._fetch_transactions()
            else:
                status.set_user("SettleUp", 0)
                self.notify("No groups found.", severity="warning")
        except SettleUpError as exc:
            status.set_error(str(exc))
            self.notify(str(exc), severity="error")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "group-select":
            group_id = str(event.value)
            self._current_group = next((g for g in self._groups if g.id == group_id), None)
            self._refresh()

    async def _fetch_transactions(self) -> None:
        if not self._current_group:
            return
        client = self.app.su_client  # type: ignore[attr-defined]
        status = self.query_one(StatusBar)
        table = self.query_one("#tx-table", DataTable)
        status.set_loading(True)
        try:
            self._members = await client.get_members(self._current_group.id)
            self._transactions = await client.get_transactions(self._current_group.id)

            if self._search_query:
                q = self._search_query.lower()
                self._transactions = [t for t in self._transactions if q in t.purpose.lower()]

            table.clear()
            for tx in self._transactions:
                payer_id = tx.payer_id
                payer_name = self._members.get(payer_id, SUMember(payer_id, payer_id or "?")).name
                table.add_row(
                    tx.display_date,
                    tx.purpose,
                    f"{tx.total_amount:.2f}",
                    tx.currency_code,
                    payer_name,
                )
            status.set_user(f"SettleUp · {self._current_group.name}", len(self._transactions))
        except SettleUpError as exc:
            status.set_error(str(exc))
            self.notify(str(exc), severity="error")

    @work(exclusive=True)
    async def _refresh(self) -> None:
        await self._fetch_transactions()

    def on_search_bar_changed(self, event: SearchBar.Changed) -> None:
        self._search_query = event.query
        self._refresh()

    def _selected_tx(self) -> SUTransaction | None:
        table = self.query_one("#tx-table", DataTable)
        row = table.cursor_row
        if row < 0 or row >= len(self._transactions):
            return None
        return self._transactions[row]

    def action_focus_search(self) -> None:
        self.query_one(SearchBar).focus_input()

    def action_clear_search(self) -> None:
        self.query_one(SearchBar).clear()
        self._search_query = ""
        self._refresh()

    def action_refresh(self) -> None:
        self._refresh()

    def action_move_down(self) -> None:
        table = self.query_one("#tx-table", DataTable)
        table.move_cursor(row=table.cursor_row + 1)

    def action_move_up(self) -> None:
        table = self.query_one("#tx-table", DataTable)
        table.move_cursor(row=table.cursor_row - 1)

    def action_quit(self) -> None:
        self.app.exit()

    def action_add_transaction(self) -> None:
        if not self._current_group:
            self.notify("Select a group first.", severity="warning")
            return
        screen = SettleUpAddScreen(
            members=self._members,
            default_currency=self._current_group.currency,
        )
        self.app.push_screen(screen, self._on_add_result)

    @work(exclusive=False)
    async def _on_add_result(self, tx: SUTransaction | None) -> None:
        if tx is None or not self._current_group:
            return
        client = self.app.su_client  # type: ignore[attr-defined]
        try:
            await client.create_transaction(self._current_group.id, tx)
            self.notify("Transaction added.", severity="information")
            await self._fetch_transactions()
        except SettleUpError as exc:
            self.notify(f"Failed to add: {exc}", severity="error")

    def action_edit_transaction(self) -> None:
        tx = self._selected_tx()
        if tx is None:
            self.notify("No transaction selected.", severity="warning")
            return
        screen = SettleUpEditScreen(tx=tx, members=self._members)
        self.app.push_screen(screen, lambda changes: self._on_edit_result(tx, changes))

    @work(exclusive=False)
    async def _on_edit_result(self, tx: SUTransaction, changes: dict | None) -> None:
        if changes is None or not self._current_group:
            return
        client = self.app.su_client  # type: ignore[attr-defined]
        try:
            field_map = {
                "purpose": "purpose",
                "currencyCode": "currency_code",
                "whoPaid": "who_paid",
                "items": "items",
            }
            for k, v in changes.items():
                attr = field_map.get(k)
                if attr:
                    setattr(tx, attr, v)
                elif k == "dateTime":
                    from ..settleup.models import _parse_dt
                    tx.date_time = _parse_dt(v)
            await client.update_transaction(self._current_group.id, tx)
            self.notify("Transaction updated.", severity="information")
            await self._fetch_transactions()
        except SettleUpError as exc:
            self.notify(f"Failed to update: {exc}", severity="error")

    def action_delete_transaction(self) -> None:
        tx = self._selected_tx()
        if tx is None:
            self.notify("No transaction selected.", severity="warning")
            return
        screen = ConfirmDeleteScreen(expense_id=0, description=tx.purpose)
        self.app.push_screen(screen, lambda confirmed: self._on_delete_result(tx.id, confirmed))

    @work(exclusive=False)
    async def _on_delete_result(self, tx_id: str, confirmed: bool) -> None:
        if not confirmed or not self._current_group:
            return
        client = self.app.su_client  # type: ignore[attr-defined]
        try:
            await client.delete_transaction(self._current_group.id, tx_id)
            self.notify("Transaction deleted.", severity="information")
            await self._fetch_transactions()
        except SettleUpError as exc:
            self.notify(f"Failed to delete: {exc}", severity="error")
