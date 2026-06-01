from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, LoadingIndicator
from textual.containers import Vertical, Horizontal, ScrollableContainer

from ..api.models import Expense, Friend, Group


class AddExpenseScreen(ModalScreen[Expense | None]):
    """Form to create a new expense."""

    CSS = """
    AddExpenseScreen {
        align: center middle;
    }
    #add-dialog {
        background: $surface;
        border: thick $primary;
        padding: 1 2;
        width: 72;
        height: auto;
        max-height: 90vh;
    }
    #add-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    .field-label { color: $text-muted; margin-top: 1; }
    .field-input { width: 1fr; }
    .field-select { width: 1fr; }
    #btn-row {
        layout: horizontal;
        height: 3;
        margin-top: 1;
        align: right middle;
    }
    #btn-row Button { margin-left: 1; }
    #split-section { margin-top: 1; }
    #split-info { color: $text-muted; }
    """

    def __init__(
        self,
        friends: list[Friend],
        groups: list[Group],
        current_user_id: int,
        default_currency: str = "USD",
    ) -> None:
        super().__init__()
        self.friends = friends
        self.groups = groups
        self.current_user_id = current_user_id
        self.default_currency = default_currency

    def compose(self) -> ComposeResult:
        group_options = [(g.name, str(g.id)) for g in self.groups]
        friend_options = [(f.full_name, str(f.id)) for f in self.friends]

        split_with_options: list[tuple[str, str]] = [("(no one — just me)", "none")]
        split_with_options += [(f"Group: {n}", f"group:{v}") for n, v in group_options]
        split_with_options += [(f"Friend: {n}", f"friend:{v}") for n, v in friend_options]

        currency_options = [
            ("USD", "USD"), ("EUR", "EUR"), ("INR", "INR"),
            ("GBP", "GBP"), ("CAD", "CAD"), ("AUD", "AUD"),
        ]

        with ScrollableContainer(id="add-dialog"):
            yield Label("Add Expense", id="add-title")

            yield Label("Description", classes="field-label")
            yield Input(placeholder="e.g. Dinner", id="inp-description", classes="field-input")

            yield Label("Cost", classes="field-label")
            yield Input(placeholder="0.00", id="inp-cost", classes="field-input")

            yield Label("Currency", classes="field-label")
            yield Select(
                [(label, value) for label, value in currency_options],
                value=self.default_currency,
                id="sel-currency",
                classes="field-select",
            )

            yield Label("Split with", classes="field-label")
            yield Select(
                [(label, value) for label, value in split_with_options],
                value="none",
                id="sel-split-with",
                classes="field-select",
            )

            yield Label("Split type", classes="field-label")
            yield Select(
                [
                    ("Equal split (50/50)", "equal"),
                    ("You paid, they owe all", "you_paid_they_owe"),
                    ("They paid, you owe all", "they_paid_you_owe"),
                ],
                value="equal",
                id="sel-split-type",
                classes="field-select",
            )

            with Horizontal(id="btn-row"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Add", variant="primary", id="btn-add")

    def _build_payload(self) -> dict | None:
        description = self.query_one("#inp-description", Input).value.strip()
        cost_str = self.query_one("#inp-cost", Input).value.strip()
        currency = str(self.query_one("#sel-currency", Select).value)
        split_with = str(self.query_one("#sel-split-with", Select).value)
        split_type = str(self.query_one("#sel-split-type", Select).value)

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

        if split_with == "none":
            # Personal expense: current user paid and owes everything
            payload["users__0__user_id"] = str(self.current_user_id)
            payload["users__0__paid_share"] = f"{cost:.2f}"
            payload["users__0__owed_share"] = f"{cost:.2f}"
        elif split_with.startswith("group:"):
            group_id = split_with.split(":", 1)[1]
            payload["group_id"] = group_id
            # Group expenses: let Splitwise split equally if no explicit shares
        elif split_with.startswith("friend:"):
            friend_id = split_with.split(":", 1)[1]
            half = cost / 2

            if split_type == "equal":
                payload["users__0__user_id"] = str(self.current_user_id)
                payload["users__0__paid_share"] = f"{cost:.2f}"
                payload["users__0__owed_share"] = f"{half:.2f}"
                payload["users__1__user_id"] = friend_id
                payload["users__1__paid_share"] = "0.00"
                payload["users__1__owed_share"] = f"{half:.2f}"
            elif split_type == "you_paid_they_owe":
                payload["users__0__user_id"] = str(self.current_user_id)
                payload["users__0__paid_share"] = f"{cost:.2f}"
                payload["users__0__owed_share"] = "0.00"
                payload["users__1__user_id"] = friend_id
                payload["users__1__paid_share"] = "0.00"
                payload["users__1__owed_share"] = f"{cost:.2f}"
            else:  # they_paid_you_owe
                payload["users__0__user_id"] = str(self.current_user_id)
                payload["users__0__paid_share"] = "0.00"
                payload["users__0__owed_share"] = f"{cost:.2f}"
                payload["users__1__user_id"] = friend_id
                payload["users__1__paid_share"] = f"{cost:.2f}"
                payload["users__1__owed_share"] = "0.00"

        return payload

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-add":
            payload = self._build_payload()
            if payload is not None:
                self.dismiss(payload)  # type: ignore[arg-type]

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
