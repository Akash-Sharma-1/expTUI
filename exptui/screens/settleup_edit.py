from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select

from ..settleup.models import SUMember, SUTransaction


class SettleUpEditScreen(ModalScreen[dict | None]):
    """Edit an existing SettleUp transaction. Returns changed fields dict on save."""

    CSS = """
    SettleUpEditScreen { align: center middle; }
    #su-edit-dialog {
        background: $surface; border: thick $primary;
        padding: 1 2; width: 72; height: auto; max-height: 90vh;
    }
    #su-edit-title { text-style: bold; color: $accent; margin-bottom: 1; }
    .field-label { color: $text-muted; margin-top: 1; }
    .field-input { width: 1fr; }
    .field-select { width: 1fr; }
    #btn-row { layout: horizontal; height: 3; margin-top: 1; align: right middle; }
    #btn-row Button { margin-left: 1; }
    """

    def __init__(self, tx: SUTransaction, members: dict[str, SUMember]) -> None:
        super().__init__()
        self.tx = tx
        self.members = members

    def compose(self) -> ComposeResult:
        currency_options = [
            ("INR", "INR"), ("USD", "USD"), ("EUR", "EUR"),
            ("GBP", "GBP"), ("CAD", "CAD"), ("AUD", "AUD"),
        ]
        exp_currency = self.tx.currency_code
        if not any(v == exp_currency for _, v in currency_options):
            currency_options.insert(0, (exp_currency, exp_currency))

        member_options = [(m.name, mid) for mid, m in self.members.items() if m.active]
        current_payer = next(iter(self.tx.who_paid), None)

        with ScrollableContainer(id="su-edit-dialog"):
            yield Label(f"Edit Transaction", id="su-edit-title")

            yield Label("Purpose", classes="field-label")
            yield Input(
                value=self.tx.purpose,
                placeholder="e.g. Dinner",
                id="inp-purpose",
                classes="field-input",
            )

            yield Label("Amount", classes="field-label")
            yield Input(
                value=f"{self.tx.total_amount:.2f}",
                placeholder="0.00",
                id="inp-amount",
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
                value=self.tx.display_date,
                placeholder="YYYY-MM-DD",
                id="inp-date",
                classes="field-input",
            )

            yield Label("Who paid", classes="field-label")
            yield Select(
                [(label, value) for label, value in member_options],
                value=current_payer or (member_options[0][1] if member_options else Select.BLANK),
                id="sel-who-paid",
                classes="field-select",
            )

            with Horizontal(id="btn-row"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Save", variant="primary", id="btn-save")

    def _build_changes(self) -> dict | None:
        purpose = self.query_one("#inp-purpose", Input).value.strip()
        amount_str = self.query_one("#inp-amount", Input).value.strip()
        currency = str(self.query_one("#sel-currency", Select).value)
        date_str = self.query_one("#inp-date", Input).value.strip()
        who_paid_id = str(self.query_one("#sel-who-paid", Select).value)

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

        # whoPaid: weight "1" = this person paid; actual amount in items[].amount
        who_paid = [{"memberId": who_paid_id, "weight": "1"}]

        # Preserve existing forWhom member list; just keep weights as-is (equal "1")
        existing_for_whom = []
        if self.tx.items:
            existing_for_whom = self.tx.items[0].get("forWhom") or []
        if not existing_for_whom:
            active_members = {mid: m for mid, m in self.members.items() if m.active}
            existing_for_whom = [{"memberId": mid, "weight": "1"} for mid in active_members]

        items = [{"amount": f"{amount:.2f}", "forWhom": existing_for_whom}]

        changes: dict = {
            "purpose": purpose,
            "currencyCode": currency,
            "whoPaid": who_paid,
            "items": items,
        }
        if date_str:
            # Convert YYYY-MM-DD to unix ms
            try:
                from datetime import datetime, timezone
                dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                changes["dateTime"] = int(dt.timestamp() * 1000)
            except ValueError:
                pass
        return changes

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-save":
            changes = self._build_changes()
            if changes is not None:
                self.dismiss(changes)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
