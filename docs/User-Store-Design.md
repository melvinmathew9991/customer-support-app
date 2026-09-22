# Real user store — design (Sprint 4, Phases.md Phase 7)

**Status:** accepted 2026-09-22. The maintainer chose SQLite as the backend and explicitly
punted the second-factor question (recorded as decision 2).

**Goal (Sprints.md):** swapping the mock user DB for a real one is a one-line config
change, not a code change in `agents/`; identification metrics on the golden set don't
regress; the mock stays available as a test fixture.

## What exists today

`tools/user_info_db.py` - two module-level LangChain `@tool` functions closing directly
over two hardcoded Python lists (4 users: Michael Jackson, John Doe, Carl Sagan, XYZ).
`agents/support.py`'s `UserInfoChainBasedEdge` imports and binds them by name at
class-definition time - that import is the coupling Phase 7 exists to break. Matching
rules to preserve exactly: email compared case-insensitively (surrounding whitespace
stripped), phone compared by digits only (any spacing/punctuation), a bare digit run
under 6 digits never matches.

## Design

**One `UserStore` `Protocol`** (`tools/user_store.py`, structural typing - no ABC, no
registration):
```python
class UserStore(Protocol):
    def search_user_info(self, query: str) -> list[dict]: ...
    def search_user_subscription(self, user_id: str) -> list[dict]: ...
```
Same signatures and return shape as today's two tool functions, so the LangChain `@tool`
wrappers become thin closures over whichever store instance the edge holds, built at
`UserInfoChainBasedEdge.__init__` time instead of imported as module globals.

**One canonical fixture.** The current 4-user list and 3-row subscription list live once,
in `tools/user_store.py`, and both stores read that same literal. `MockUserStore` holds it
in memory (today's behavior, unchanged). `SqliteUserStore` seeds a real `users`/
`subscriptions` table from that same literal the first time it opens an empty database.
Because both stores read one source of truth, mock and real can't silently drift apart.

**Matching stays in Python, not SQL.** `SqliteUserStore.search_user_info` selects every
row, then filters with the same shared `_matching_users` helper `MockUserStore` uses.
Four rows don't need an indexed, normalized SQL column - that would be a second place to
get the matching rule right instead of one. `search_user_subscription` is an exact
`WHERE user_id = ?`, since that lookup is already exact today.

**Auto-seed, not a seed script.** `SqliteUserStore.__init__` creates the schema and seeds
it if the `users` table is empty, mirroring `SessionStore`'s self-healing-on-open posture.
No manual step to forget, no drift between "the docs say run the seed script" and what's
actually in the file.

**Config-driven, like every other provider in this project.**
```python
user_store_provider: Literal["mock", "sqlite"] = "sqlite"
user_store_db_path: Path = PROJECT_ROOT / "data" / "users.sqlite"
```
mirroring `llm_provider`/`get_chat_model()`. `get_user_store()` in `config.py` resolves
it. `pipeline.py`'s `_get_pipeline()` calls it and passes the result into
`UserInfoChainBasedEdge`. Default is `sqlite` - the "real" store - since seeding is
byte-identical to the mock, this is transparent to every existing caller and to the
golden-set harness's scores.

**`UserInfoChainBasedEdge(user_store: UserStore = MockUserStore())`.** The default
preserves every current call site and all 335 existing tests with zero changes; only
`pipeline.py`'s production wiring actually passes the sqlite-backed store.

## Out of scope

External/Shopify API integration. A second identification factor (decision 2, below).
Write operations - this is a read-only lookup, same as today. Encryption at rest for
`users.sqlite` (same posture as `sessions.sqlite`). Any change to
`UserInfoChainBasedEdge`'s identification *logic* - only where it gets its data changes.

## Tests

- **Contract tests** (`tests/tools/test_user_store.py`): today's
  `tests/tools/test_user_info_db.py` cases, parametrized over both `MockUserStore()` and a
  fresh `SqliteUserStore(tmp_path)` - same assertions, both backends, so behavior drift
  fails a test instead of shipping.
- **`SqliteUserStore`-only**: auto-seed on an empty file; reopening an already-seeded file
  doesn't duplicate rows; a missing parent directory is created, not a crash.
- **`UserInfoChainBasedEdge`**: existing tests pass unmodified (default-arg backward
  compatibility); one new test confirms it works identically when constructed with a
  `SqliteUserStore`.
- **Regression gate**: one full 135-entry golden-set run with `user_store_provider=sqlite`
  (the new default), diffed against the current baseline report with
  `scripts/summarize_eval_runs.py` - identification success and fails-safe rate must be
  unchanged; nothing else should move since no other layer changed.
- **Live check**: CLI identify-by-email and identify-by-phone against the sqlite backend,
  same shape as `report.md` §10.2's Conversation A/B.

## Decisions

1. **Backend.** *Chosen:* SQLite via the standard library, same pattern as
   `session_store.py`. *Alternative considered:* a mock external HTTP API (rejected - adds
   a service to run, retries, and auth headers for no metric benefit) or the real Shopify
   Admin API (rejected - needs external credentials, sends real PII to a third party, and
   is out of proportion to the rest of this project).
2. **Second identification factor.** *Chosen:* punt, explicitly. Identification stays a
   lookup, not authentication - the current behavior (anyone who knows an email/phone is
   served that tier) is unchanged. Recorded here so it isn't silently forgotten, the same
   way #14's license question was tracked until decided. *Alternative considered:* require
   a second field (e.g. email + last name) before a lookup succeeds - rejected for this
   sprint since it expands into `agents/support.py`'s identification flow itself, not just
   the storage layer Phase 7 scopes.
