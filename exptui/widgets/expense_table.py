from __future__ import annotations

from textual.widgets import DataTable

from ..api.models import Expense


COLUMNS = [
    ("Date", 12),
    ("Description", 40),
    ("Cost", 10),
    ("Currency", 8),
    ("My Share", 10),
    ("Paid", 10),
]


class ExpenseTable(DataTable):
    """DataTable showing Splitwise expenses. Maintains expense_ids in sync with rows."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.expense_ids: list[int] = []
        self._expenses: list[Expense] = []

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        for name, width in COLUMNS:
            self.add_column(name, width=width)

    def update_expenses(self, expenses: list[Expense], current_user_id: int = 0) -> None:
        self.expense_ids = []
        self._expenses = expenses
        self.clear()
        for expense in expenses:
            self.expense_ids.append(expense.id)
            my_share = ""
            paid = ""
            if current_user_id:
                for split in expense.users:
                    if split.user_id == current_user_id:
                        my_share = split.owed_share
                        paid = split.paid_share
                        break
            self.add_row(
                expense.display_date,
                expense.description,
                expense.cost,
                expense.currency_code,
                my_share,
                paid,
            )

    def get_selected_expense_id(self) -> int | None:
        if not self.expense_ids:
            return None
        row = self.cursor_row
        if row < 0 or row >= len(self.expense_ids):
            return None
        return self.expense_ids[row]

    def get_selected_expense(self) -> Expense | None:
        if not self._expenses:
            return None
        row = self.cursor_row
        if row < 0 or row >= len(self._expenses):
            return None
        return self._expenses[row]

