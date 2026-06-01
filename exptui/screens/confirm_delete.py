from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Label
from textual.containers import Vertical, Horizontal


class ConfirmDeleteScreen(ModalScreen[bool]):
    """Confirm before deleting an expense."""

    CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }
    #confirm-dialog {
        background: $surface;
        border: thick $error;
        padding: 2 3;
        width: 60;
        height: auto;
    }
    #confirm-title {
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }
    #confirm-msg {
        margin-bottom: 1;
    }
    #btn-row {
        layout: horizontal;
        height: 3;
        align: right middle;
    }
    #btn-row Button {
        margin-left: 1;
    }
    """

    def __init__(self, expense_id: int, description: str) -> None:
        super().__init__()
        self.expense_id = expense_id
        self.description = description

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label("Delete Expense", id="confirm-title")
            yield Label(
                f'Delete "{self.description}"? This cannot be undone.',
                id="confirm-msg",
            )
            with Horizontal(id="btn-row"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Delete", variant="error", id="btn-delete")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-delete":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)
