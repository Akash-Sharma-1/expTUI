from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label


class SearchBar(Widget):
    DEFAULT_CSS = """
    SearchBar {
        layout: horizontal;
        height: 3;
        align: left middle;
    }
    SearchBar Label {
        width: auto;
        padding: 0 1 0 0;
        color: $text-muted;
    }
    """

    class Changed(Message):
        def __init__(self, query: str) -> None:
            super().__init__()
            self.query = query

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._debounce_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        yield Label("Search:")
        yield Input(placeholder="filter by description...", id="search-input")

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
        self._debounce_task = asyncio.get_event_loop().create_task(
            self._emit_after_delay(event.value)
        )

    async def _emit_after_delay(self, query: str) -> None:
        await asyncio.sleep(0.3)
        self.post_message(self.Changed(query))

    def focus_input(self) -> None:
        self.query_one(Input).focus()

    def clear(self) -> None:
        self.query_one(Input).value = ""
