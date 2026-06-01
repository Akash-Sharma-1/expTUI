# CLAUDE.md

## Project

Python + Textual TUI for managing expenses on Splitwise and Settle Up.
Package name: `exptui`. Entry point: `python -m exptui`.

## Run

```bash
pip install -r requirements.txt
python -m exptui
```

Config: `~/.config/exp-tui/config.toml`

---

## Architecture

```
SplitwiseTUIApp (__main__.py)
  ├── both configured  → ProviderSelectScreen → routes by user choice
  ├── Splitwise only   → screens/main.py       → api/client.py
  └── Settle Up only   → screens/settleup_main.py → settleup/client.py
```

---

## Config (`config.py`)

- `load_config()` → `Config` dataclass
- TOML via `tomli` (Python 3.10), `tomllib` stdlib (3.11+)
- Env vars take priority over file values
  - `SPLITWISE_API_KEY`
  - `SETTLEUP_FIREBASE_API_KEY`, `SETTLEUP_REFRESH_TOKEN`, `SETTLEUP_UID`
- `Config.has_splitwise` / `Config.has_settleup` — bool presence checks
- Raises `ConfigError` (printed to stderr, exit 1) if neither provider configured

---

## Splitwise (`api/`)

- `SplitwiseClient` — `httpx.AsyncClient`, `Authorization: Bearer <key>`
- Base URL: `https://secure.splitwise.com/api/v3.0`
- **Quirk:** `GET /get_current_user` returns key `"user"`, not `"current_user"`
  — handled with `.get("current_user") or data["user"]`
- All methods return typed dataclasses (`api/models.py`)
- Typed exceptions: `AuthError`, `NotFoundError`, `RateLimitError`, `ServerError`
- `close()` called in `App.on_unmount` to release httpx connection pool

---

## Settle Up (`settleup/`)

### Auth (`settleup/auth.py`)

- `FirebaseAuth(api_key, refresh_token)` — exchanges refresh token for ID token
- Token endpoint: `POST https://securetoken.googleapis.com/v1/token`
- **CRITICAL: must send `Referer: https://settleup.app` + `Origin: https://settleup.app`**
  — Firebase API key is HTTP-referrer-restricted; without header → 403 `API_KEY_HTTP_REFERRER_BLOCKED`
- Token cached in memory; re-fetches 60 s before expiry
- When Firebase rotates the refresh token, new value is written back to `config.toml`

### Client (`settleup/client.py`)

- `SettleUpClient(uid, auth)` — Firebase Realtime Database REST
- Base URL: `https://settle-up-live.firebaseio.com`
- ID token passed as `?auth=<token>` query param on every request
- After any create/update/delete: fires `serverTasks/calculateGroupsDebts` (non-critical, fire-and-forget)
- Delete uses HTTP `DELETE` on `/transactions/{groupId}/{txId}.json`

### Transaction shape (actual Firebase format — differs from docs)

```json
{
  "purpose": "Dinner",
  "currencyCode": "INR",
  "dateTime": 1779890505934,
  "type": "expense",
  "whoPaid": [{"memberId": "abc", "weight": "1"}],
  "items": [
    {
      "amount": "950",
      "forWhom": [
        {"memberId": "abc", "weight": "1"},
        {"memberId": "xyz", "weight": "1"}
      ]
    }
  ],
  "exchangeRates": {"INR": "1"},
  "fixedExchangeRate": false
}
```

**Key facts:**
- `dateTime` = Unix **milliseconds** integer (not ISO string). `_parse_dt()` handles both.
- `whoPaid[].weight` = **ratio** (single payer = `"1"`), NOT the amount paid
- Actual amount = `items[].amount` — always use this for display and total
- `forWhom[].weight` = relative split weights; equal split = all `"1"`
- Old transactions (pre-2025) stored actual amount in `whoPaid[].weight` — `total_amount` property falls back to this if `items` is empty

---

## Screens

All `Screen` or `ModalScreen` subclasses. No business logic in screens — API calls go through client.

| Screen | File | Returns |
|--------|------|---------|
| Provider select | `screens/provider_select.py` | `"splitwise"` \| `"settleup"` |
| Splitwise list | `screens/main.py` | — |
| Splitwise add | `screens/add_expense.py` | payload `dict` |
| Splitwise edit | `screens/edit_expense.py` | payload `dict` |
| Delete confirm | `screens/confirm_delete.py` | `bool` |
| Settle Up list | `screens/settleup_main.py` | — |
| Settle Up add | `screens/settleup_add.py` | `SUTransaction` |
| Settle Up edit | `screens/settleup_edit.py` | changes `dict` |

**Modal pattern:** `self.app.push_screen(Screen(), callback)` — callback receives dismissed value.  
**Worker pattern:** `@work(exclusive=True)` on all API-calling methods — prevents stacking on rapid input.

---

## Widgets

- `ExpenseTable` (`widgets/expense_table.py`) — `DataTable` subclass; maintains parallel `expense_ids: list[int]` and `_expenses: list[Expense]` in sync with rows. Instance vars (not class vars) to avoid shared-state bugs.
- `SearchBar` (`widgets/search_bar.py`) — debounced 300 ms Input; cancels prior `asyncio.Task` on each keystroke; emits `SearchBar.Changed(query)` message.
- `StatusBar` (`widgets/status_bar.py`) — docked-bottom `Static`; shows user/group name, count, keybinding hints.

---

## Styles

`styles/app.tcss` — all layout and colour. No inline CSS in Python.  
`CSS_PATH` set on `SplitwiseTUIApp` as absolute path via `Path(__file__).parent`.

---

## Key gotchas (in order of "will waste your time")

1. **Settle Up Referer** — `Referer: https://settleup.app` required on token refresh or 403
2. **Settle Up amount field** — read from `items[].amount`, not `whoPaid[].weight`
3. **Settle Up dateTime** — integer Unix ms, not string; `_parse_dt()` handles both formats
4. **Splitwise get_current_user** — response key is `"user"`, not `"current_user"`
5. **Textual event loop** — all httpx calls must be in `@work` async workers; sync calls block the TUI
6. **ExpenseTable class vars** — `expense_ids`/`_expenses` must be instance vars; class-level mutable defaults are shared across instances in Python

---

## Dependencies

```
textual>=0.89.1
httpx>=0.28.0
tomli>=2.0.0 ; python_version < "3.11"
```
