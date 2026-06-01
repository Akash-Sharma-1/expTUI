from __future__ import annotations

from textual.widget import Widget
from textual.reactive import reactive


class StatusBar(Widget):
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 2;
        dock: bottom;
    }
    """

    _text: reactive[str] = reactive("Loading...")

    def render(self) -> str:
        return self._text

    def set_user(self, name: str, count: int) -> None:
        self._text = f" {name}  |  {count} expenses  |  [a]dd [e]dit [d]elete [/]search [r]efresh [q]uit"

    def set_loading(self, loading: bool) -> None:
        if loading:
            self._text = " Loading..."

    def set_error(self, msg: str) -> None:
        self._text = f" Error: {msg}"
