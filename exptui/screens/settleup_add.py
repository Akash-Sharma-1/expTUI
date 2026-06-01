from __future__ import annotations

from datetime import datetime, timezone

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select

from ..settleup.models import SUMember, SUTransaction, generate_push_id


class SettleUpAddScreen(ModalScreen[SUTransaction | None]):
    CSS = """
    SettleUpAddScreen { align: center middle; }
    #su-add-dialog {
        background: $surface; border: thick $primary;
        padding: 1 2; width: 72; height: auto; max-height: 90vh;
    }
    #su-add-title { text-style: bold; color: $accent; margin-bottom: 1; }
    .field-label { color: $text-muted; margin-top: 1; }
    .field-input { width: 1fr; }
    .field-select { width: 1fr; }
    #btn-row { layout: horizontal; height: 3; margin-top: 1; align: right middle; }
    #btn-row Button { margin-left: 1; }
    """

    def __init__(self, members: dict[str, SUMember], default_currency: str = "INR") -> None:
        super().__init__()
        self.members = members
        self.default_currency = default_currency

    def compose(self) -> ComposeResult:
        member_options = [(m.name, mid) for mid, m in self.members.items() if m.active]
        currency_options = [
            ("INR", "INR"), ("USD", "USD"), ("EUR", "EUR"),
            ("GBP", "GBP"), ("CAD", "CAD"), ("AUD", "AUD"),
        ]

        with ScrollableContainer(id="su-add-dialog"):
            yield Label("Add Transaction", id="su-add-title")

            yield Label("Purpose", classes="field-label")
            yield Input(placeholder="e.g. Dinner", id="inp-purpose", classes="field-input")

            yield Label("Amount", classes="field-label")
            yield Input(placeholder="0.00", id="inp-amount", classes="field-input")

            yield Label("Currency", classes="field-label")
            yield Select(
                [(label, value) for label, value in currency_options],
                value=self.default_currency,
                id="sel-currency",
                classes="field-select",
            )

            yield Label("Who paid", classes="field-label")
            yield Select(
                [(label, value) for label, value in member_options],
                value=member_options[0][1] if member_options else Select.BLANK,
                id="sel-who-paid",
                classes="field-select",
            )

            yield Label("Split type", classes="field-label")
            yield Select(
                [
                    ("Equal among all members", "equal"),
                    ("Paid for self only (personal expense)", "self"),
                ],
                value="equal",
                id="sel-split",
                classes="field-select",
            )

            with Horizontal(id="btn-row"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Add", variant="primary", id="btn-add")

    def _build_transaction(self) -> SUTransaction | None:
        purpose = self.query_one("#inp-purpose", Input).value.strip()
        amount_str = self.query_one("#inp-amount", Input).value.strip()
        currency = str(self.query_one("#sel-currency", Select).value)
        who_paid_id = str(self.query_one("#sel-who-paid", Select).value)
        split_type = str(self.query_one("#sel-split", Select).value)

        if not purpose:
            self.notify("Purpose required.", severity="error")
            return None
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            self.notify("Amount must be a positive number.", severity="error")
            return None

        active_members = {mid: m for mid, m in self.members.items() if m.active}

        # whoPaid: weight "1" means this person paid; actual amount is in items[].amount
        who_paid = [{"memberId": who_paid_id, "weight": "1"}]

        if split_type == "equal" and active_members:
            for_whom_list = [{"memberId": mid, "weight": "1"} for mid in active_members]
        else:
            for_whom_list = [{"memberId": who_paid_id, "weight": "1"}]

        items = [{"amount": f"{amount:.2f}", "forWhom": for_whom_list}]

        return SUTransaction(
            id=generate_push_id(),
            purpose=purpose,
            currency_code=currency,
            date_time=datetime.now(timezone.utc),
            tx_type="expense",
            who_paid=who_paid,
            items=items,
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-add":
            tx = self._build_transaction()
            if tx is not None:
                self.dismiss(tx)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
