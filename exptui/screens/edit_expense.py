from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select
from textual.containers import Horizontal, ScrollableContainer

from ..api.models import Expense, Friend, Group


class EditExpenseScreen(ModalScreen[dict | None]):
    """Form to edit an existing expense. Returns payload dict on save, None on cancel."""

    CSS = """
    EditExpenseScreen {
        align: center middle;
    }
    #edit-dialog {
        background: $surface;
        border: thick $primary;
        padding: 1 2;
        width: 72;
        height: auto;
        max-height: 90vh;
    }
    #edit-title { text-style: bold; color: $accent; margin-bottom: 1; }
    .field-label { color: $text-muted; margin-top: 1; }
    .field-input { width: 1fr; }
    .field-select { width: 1fr; }
    #btn-row { layout: horizontal; height: 3; margin-top: 1; align: right middle; }
    #btn-row Button { margin-left: 1; }
    """

    def __init__(
        self,
        expense: Expense,
        friends: list[Friend],
        groups: list[Group],
        current_user_id: int,
    ) -> None:
        super().__init__()
        self.expense = expense
        self.friends = friends
        self.groups = groups
        self.current_user_id = current_user_id

    def compose(self) -> ComposeResult:
        currency_options = [
            ("USD", "USD"), ("EUR", "EUR"), ("INR", "INR"),
            ("GBP", "GBP"), ("CAD", "CAD"), ("AUD", "AUD"),
        ]
        # Make sure expense currency is in the list
        exp_currency = self.expense.currency_code
        if not any(v == exp_currency for _, v in currency_options):
            currency_options.insert(0, (exp_currency, exp_currency))

        with ScrollableContainer(id="edit-dialog"):
            yield Label(f"Edit Expense #{self.expense.id}", id="edit-title")

            yield Label("Description", classes="field-label")
            yield Input(
                value=self.expense.description,
                placeholder="e.g. Dinner",
                id="inp-description",
                classes="field-input",
            )

            yield Label("Cost", classes="field-label")
            yield Input(
                value=self.expense.cost,
                placeholder="0.00",
                id="inp-cost",
                classes="field-input",
            )

            yield Label("Currency", classes="field-label")
            yield Select(
                [(label, value) for label, value in currency_options],
                value=exp_currency,
                id="sel-currency",
                classes="field-select",
            )

            yield Label("Date (YYYY-MM-DD)", classes="field-label")
            yield Input(
                value=self.expense.display_date,
                placeholder="YYYY-MM-DD",
                id="inp-date",
                classes="field-input",
            )

            with Horizontal(id="btn-row"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Save", variant="primary", id="btn-save")

    def _build_payload(self) -> dict | None:
        description = self.query_one("#inp-description", Input).value.strip()
        cost_str = self.query_one("#inp-cost", Input).value.strip()
        currency = str(self.query_one("#sel-currency", Select).value)
        date_str = self.query_one("#inp-date", Input).value.strip()

        if not description:
            self.notify("Description required.", severity="error")
            return None
        try:
            cost = float(cost_str)
            if cost <= 0:
                raise ValueError
        except ValueError:
            self.notify("Cost must be a positive number.", severity="error")
            return None

        payload: dict = {
            "cost": f"{cost:.2f}",
            "description": description,
            "currency_code": currency,
        }
        if date_str:
            payload["date"] = date_str

        return payload

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-save":
            payload = self._build_payload()
            if payload is not None:
                self.dismiss(payload)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
