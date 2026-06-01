from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header
from textual.containers import Vertical
from textual import work

from ..api.client import SplitwiseError
from ..api.models import Expense, Friend, Group, User
from ..widgets.expense_table import ExpenseTable
from ..widgets.search_bar import SearchBar
from ..widgets.status_bar import StatusBar
from .add_expense import AddExpenseScreen
from .edit_expense import EditExpenseScreen
from .confirm_delete import ConfirmDeleteScreen


class MainScreen(Screen):
    BINDINGS = [
        ("a", "add_expense", "Add"),
        ("e", "edit_expense", "Edit"),
        ("d", "delete_expense", "Delete"),
        ("slash", "focus_search", "Search"),
        ("r", "refresh", "Refresh"),
        ("j", "move_down", "Down"),
        ("k", "move_up", "Up"),
        ("q", "quit", "Quit"),
        ("escape", "clear_search", "Clear"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._current_user: User | None = None
        self._friends: list[Friend] = []
        self._groups: list[Group] = []
        self._search_query: str = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="main-layout"):
            yield SearchBar(id="search-bar")
            yield ExpenseTable(id="expense-table")
        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._load_initial()

    @work(exclusive=True)
    async def _load_initial(self) -> None:
        status = self.query_one(StatusBar)
        status.set_loading(True)
        try:
            client = self.app.client  # type: ignore[attr-defined]
            self._current_user = await client.get_current_user()
            self._friends, self._groups = await self._load_friends_and_groups(client)
            await self._fetch_expenses()
        except SplitwiseError as exc:
            status.set_error(str(exc))
            self.notify(str(exc), severity="error")

    async def _load_friends_and_groups(self, client):
        try:
            friends = await client.get_friends()
        except SplitwiseError:
            friends = []
        try:
            groups = await client.get_groups()
        except SplitwiseError:
            groups = []
        return friends, groups

    async def _fetch_expenses(self) -> None:
        client = self.app.client  # type: ignore[attr-defined]
        status = self.query_one(StatusBar)
        table = self.query_one(ExpenseTable)
        status.set_loading(True)
        try:
            expenses = await client.get_expenses(limit=100)
            if self._search_query:
                q = self._search_query.lower()
                expenses = [e for e in expenses if q in e.description.lower()]
            uid = self._current_user.id if self._current_user else 0
            table.update_expenses(expenses, current_user_id=uid)
            name = self._current_user.full_name if self._current_user else "unknown"
            status.set_user(name, len(expenses))
        except SplitwiseError as exc:
            status.set_error(str(exc))
            self.notify(str(exc), severity="error")

    @work(exclusive=True)
    async def _refresh(self) -> None:
        await self._fetch_expenses()

    def on_search_bar_changed(self, event: SearchBar.Changed) -> None:
        self._search_query = event.query
        self._refresh()

    def action_focus_search(self) -> None:
        self.query_one(SearchBar).focus_input()

    def action_clear_search(self) -> None:
        self.query_one(SearchBar).clear()
        self._search_query = ""
        self._refresh()

    def action_refresh(self) -> None:
        self._refresh()

    def action_move_down(self) -> None:
        table = self.query_one(ExpenseTable)
        table.move_cursor(row=table.cursor_row + 1)

    def action_move_up(self) -> None:
        table = self.query_one(ExpenseTable)
        table.move_cursor(row=table.cursor_row - 1)

    def action_quit(self) -> None:
        self.app.exit()

    def action_add_expense(self) -> None:
        if self._current_user is None:
            self.notify("Still loading user info. Try again.", severity="warning")
            return
        screen = AddExpenseScreen(
            friends=self._friends,
            groups=self._groups,
            current_user_id=self._current_user.id,
            default_currency=self.app.config.default_currency,  # type: ignore[attr-defined]
        )
        self.app.push_screen(screen, self._on_add_result)

    @work(exclusive=False)
    async def _on_add_result(self, payload: dict | None) -> None:
        if payload is None:
            return
        client = self.app.client  # type: ignore[attr-defined]
        try:
            await client.create_expense(payload)
            self.notify("Expense added.", severity="information")
            await self._fetch_expenses()
        except SplitwiseError as exc:
            self.notify(f"Failed to add: {exc}", severity="error")

    def action_edit_expense(self) -> None:
        table = self.query_one(ExpenseTable)
        expense = table.get_selected_expense()
        if expense is None:
            self.notify("No expense selected.", severity="warning")
            return
        if self._current_user is None:
            self.notify("Still loading. Try again.", severity="warning")
            return
        screen = EditExpenseScreen(
            expense=expense,
            friends=self._friends,
            groups=self._groups,
            current_user_id=self._current_user.id,
        )
        self.app.push_screen(screen, lambda payload: self._on_edit_result(expense.id, payload))

    @work(exclusive=False)
    async def _on_edit_result(self, expense_id: int, payload: dict | None) -> None:
        if payload is None:
            return
        client = self.app.client  # type: ignore[attr-defined]
        try:
            await client.update_expense(expense_id, payload)
            self.notify("Expense updated.", severity="information")
            await self._fetch_expenses()
        except SplitwiseError as exc:
            self.notify(f"Failed to update: {exc}", severity="error")

    def action_delete_expense(self) -> None:
        table = self.query_one(ExpenseTable)
        expense = table.get_selected_expense()
        if expense is None:
            self.notify("No expense selected.", severity="warning")
            return
        screen = ConfirmDeleteScreen(expense_id=expense.id, description=expense.description)
        self.app.push_screen(screen, lambda confirmed: self._on_delete_result(expense.id, confirmed))

    @work(exclusive=False)
    async def _on_delete_result(self, expense_id: int, confirmed: bool) -> None:
        if not confirmed:
            return
        client = self.app.client  # type: ignore[attr-defined]
        try:
            await client.delete_expense(expense_id)
            self.notify("Expense deleted.", severity="information")
            await self._fetch_expenses()
        except SplitwiseError as exc:
            self.notify(f"Failed to delete: {exc}", severity="error")
