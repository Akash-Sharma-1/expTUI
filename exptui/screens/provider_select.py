from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Label
from textual.containers import Vertical


class ProviderSelectScreen(Screen[str]):
    """Choose between Splitwise and Settle Up."""

    CSS = """
    ProviderSelectScreen {
        align: center middle;
        background: $surface;
    }
    #provider-box {
        background: $panel;
        border: thick $primary;
        padding: 2 4;
        width: 50;
        height: auto;
    }
    #provider-title {
        text-style: bold;
        color: $accent;
        text-align: center;
        margin-bottom: 2;
    }
    .provider-btn {
        width: 1fr;
        margin-bottom: 1;
    }
    """

    def __init__(self, has_splitwise: bool, has_settleup: bool) -> None:
        super().__init__()
        self.has_splitwise = has_splitwise
        self.has_settleup = has_settleup

    def compose(self) -> ComposeResult:
        with Vertical(id="provider-box"):
            yield Label("Select Provider", id="provider-title")
            if self.has_splitwise:
                yield Button("Splitwise", variant="primary", id="btn-splitwise", classes="provider-btn")
            if self.has_settleup:
                yield Button("Settle Up", variant="success", id="btn-settleup", classes="provider-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-splitwise":
            self.dismiss("splitwise")
        elif event.button.id == "btn-settleup":
            self.dismiss("settleup")
