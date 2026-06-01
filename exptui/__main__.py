from __future__ import annotations

import sys
from pathlib import Path

from textual.app import App

from .api.client import SplitwiseClient
from .config import Config, ConfigError, load_config
from .settleup.auth import FirebaseAuth
from .settleup.client import SettleUpClient
from .screens.main import MainScreen
from .screens.settleup_main import SettleUpMainScreen
from .screens.provider_select import ProviderSelectScreen


class SplitwiseTUIApp(App):
    CSS_PATH = str(Path(__file__).parent / "styles" / "app.tcss")
    TITLE = "Expense TUI"

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config

        self.client: SplitwiseClient | None = None
        if config.has_splitwise:
            self.client = SplitwiseClient(api_key=config.api_key)

        self.su_client: SettleUpClient | None = None
        if config.has_settleup:
            auth = FirebaseAuth(
                api_key=config.su_firebase_api_key,
                refresh_token=config.su_refresh_token,
            )
            self.su_client = SettleUpClient(uid=config.su_uid, auth=auth)

    def on_mount(self) -> None:
        if self.config.has_splitwise and self.config.has_settleup:
            self.push_screen(
                ProviderSelectScreen(has_splitwise=True, has_settleup=True),
                self._on_provider_selected,
            )
        elif self.config.has_settleup:
            self.push_screen(SettleUpMainScreen())
        else:
            self.push_screen(MainScreen())

    def _on_provider_selected(self, provider: str) -> None:
        if provider == "settleup":
            self.push_screen(SettleUpMainScreen())
        else:
            self.push_screen(MainScreen())

    async def on_unmount(self) -> None:
        if self.client:
            await self.client.close()
        if self.su_client:
            await self.su_client.close()


def main() -> None:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"\n[expense-tui] Configuration error:\n\n{exc}\n", file=sys.stderr)
        sys.exit(1)

    app = SplitwiseTUIApp(config=config)
    app.run()


if __name__ == "__main__":
    main()
