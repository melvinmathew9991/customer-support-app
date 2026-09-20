# Session persistence — design (Sprint 3, Phases.md Phase 6)

**Status:** accepted 2026-09-20. The maintainer chose the recommended option on all four
[decisions](#decisions), recorded at the end. One refinement made while building: a
database written by a *newer* schema than the code knows fails loudly when the store is
opened (`Rules.md`: fail early on misconfiguration), while a single bad *row* only starts a
new session.

**Goal (Sprints.md):** killing and restarting the process mid-conversation resumes at the
same node with the full history, behind the interface `app.py` and `cli.py` already use,
and the existing test suite passes untouched.

## What a conversation is made of

Read from `pipeline.py`, `graph/`, `agents/support.py` and `app.py`. Only the first four
need saving; the rest are rebuilt or throwaway.

| State | Where it lives | Type | Save? |
|---|---|---|---|
| Message history | `CustomerSupportPipeline._message_history.messages` | list of `{"content", "role"}` dicts | **Yes** |
| Current node | `_current_node` | one of `GreetingNode`, `AuthenticatedUserNode`, `CallCustomerNode` (a fixed chain) | **Yes**, by class name |
| Input the current node was handed | `BaseNode._node_input` | `None` (greeting), `UserProfile`, `PhoneCallRequest`, or a `MessageOutput` error payload | **Yes**, as typed JSON |
| Retry counters | `BaseEdge._num_fails` on the identity and callback edges | int each | **Yes** |
| Conversation id | `_conversation_id` (a uuid) | str | **Yes**, so the turn log stays one thread across a restart |
| Graph objects, models, retrievers | built by `_get_pipeline()` and `get_chat_model()` | live objects | No: rebuilt on load |
| `_last_intermediate_steps`, LLM caches | edge attributes | transient | No |
| Streamlit `st.session_state.messages` | `app.py` | a copy of the user and assistant turns | No: rebuilt from the saved history on load |

Everything saved is plain JSON (strings, ints, and pydantic models that dump to dicts).

## Design

**A `SessionStore` (new `session_store.py`), SQLite via the standard library.** No new
dependency and no ORM, which is what `Rules.md` asks before adding a datastore. One row
per conversation, rewritten as a whole after every turn inside a transaction:

```
sessions(
  session_id  TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  node        TEXT NOT NULL,     -- GreetingNode | AuthenticatedUserNode | CallCustomerNode
  node_input  TEXT,              -- {"type": "UserProfile"|"PhoneCallRequest"|"MessageOutput", "data": {...}} or NULL
  edge_fails  TEXT NOT NULL,     -- {"UserInfoChainBasedEdge": 0, "CallCustomerEdge": 0}
  messages    TEXT NOT NULL,     -- JSON list
  is_over     INTEGER NOT NULL,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
)
```

A conversation is a few dozen short messages, so a single JSON row is simpler than a
messages table and is atomic for free. Schema versioning uses `PRAGMA user_version`, with
a small ordered list of migration functions run on open (the "migration" deliverable). Version 1 creates the table.

**Opt-in, on the pipeline.** `CustomerSupportPipeline(store=None, session_id=None)`. With no
store it behaves exactly as today, which keeps the 244 existing tests untouched and stops
the eval harness (which builds a pipeline per golden entry) from writing hundreds of
sessions. `cli.py` and `app.py` pass a store.

**Save after every completed turn**, including the timed-out path added by #30 (the user
message and the "try again" reply are both in the history). A crash in the middle of a
turn loses that turn's user message, not the conversation; the user simply sends it again.
That is deliberate: saving a half-finished turn would store a state the graph never
produced.

**Load rebuilds, it does not replay.** `_get_pipeline()` builds the graph as today; load
looks the saved node up by name among the objects it built, sets `_node_input` and the
edge counters, restores the history and conversation id, and skips the greeting. No LLM
call happens on load.

**A bad saved row is not fatal.** An unknown node name, a `node_input` of the wrong type for
its node, or unparseable JSON logs a warning and starts a new session; a corrupt row must
never stop the app from opening. A database from a newer schema is different: it is a
misconfiguration, so opening the store raises `SessionStoreError` instead of guessing.

**Settings, per `Rules.md`.** `session_db_path` in `config.py`'s `Settings`, default
`<project root>/data/sessions.sqlite`, documented in `.env.example`, and `data/` added to
`.gitignore` (runtime artifact).

## How a user gets their conversation back

The store needs a `session_id`. Getting it to the right person differs per interface:

- **Streamlit:** the id lives in the URL (`?session=<uuid>`) via `st.query_params`. A first
  visit with no id creates one and writes it to the URL; a browser refresh or a server
  restart with that URL resumes. (`st.session_state` alone cannot do this: it is lost on
  refresh.)
- **CLI:** `--session <id>` resumes that session (or starts it under that id, saying so, if it
  does not exist), `--resume` resumes the most recent unfinished one, and a bare run starts a
  new session and prints its id. Nothing resumes implicitly.

The Graph tab keeps working unchanged: it reads `pipeline._current_node`, which load sets.

## Edge cases

- **Finished conversation** (`CallCustomerNode`, `is_over`): resuming one shows the saved
  transcript and says the conversation ended; the user starts a new one (Streamlit offers a
  button, the CLI says to run it again without `--session`).
- **Failed identification.** After the identity edge exhausts its retries the graph moves
  to `AuthenticatedUserNode` with a `MessageOutput` error as its input, prints "we still
  couldn't verify your account", and then keeps answering from the free KB (confirmed
  live on 2026-09-20: after three unidentifiable messages, "How do I accept payments from
  customers?" was answered, with `AuthenticatedUserNode` holding a `MessageOutput` as its
  input). That is existing behavior, not new, and is not fixed here. Persisting it faithfully would
  make an unverified session resumable, so the proposal is: **a session whose node input is
  not a `UserProfile` is not resumed** (a new one starts). The behavior itself is tracked
  as #37; if it changes, revisit this line.
- **Profile changes between restarts.** The saved `UserProfile` (tier included) is trusted
  on resume; identification is not re-run. If the mock DB changes a user's tier mid-session,
  the session keeps the old one until it ends.
- **Knowledge base changes between restarts.** No effect: retrieval reads the live index.
- **Concurrency.** Out of scope beyond what SQLite gives by default (one writer at a time,
  the connection opened per operation). One process, one user per session id.
- **Privacy.** A saved session holds the user's name, email and phone number in the
  clear, and the Streamlit session id in the URL acts as a bearer token: anyone with the
  link can read the conversation. Acceptable for a local single-instance dev app, and it
  must be re-decided before any real deployment (Phase 10). See decision 4.

## Out of scope

Multi-user or multi-process concurrency, listing or managing sessions in the UI,
encryption at rest, authentication for resume, a real database, and migrating conversations
already in memory.

## Tests

- **Store (no LLM, no network):** save/load round trip per node type, each `node_input`
  type, corrupt JSON, unknown node, newer schema version, migration from an empty file,
  atomic rewrite.
- **Pipeline:** with a lightweight stand-in for the graph, a saved conversation resumes at
  the same node with the same history, edge counters and conversation id; a failed load
  starts fresh; no store means no file is touched.
- **Existing suite:** passes. The one edit to an existing test file is that the CLI tests
  (added in #36) now pass an empty argv to `main()`, since it now parses arguments; their
  expectations are unchanged.
- **Live check (the definition of done):** run the CLI, identify, ask a question, kill the
  process, restart with the resume option, and confirm it continues at
  `AuthenticatedUserNode` with the history intact; repeat once for Streamlit with the URL.
  Then one golden-set run with persistence off to confirm no LLM behavior moved.

## Decisions

1. **Storage.** *Recommended:* SQLite through the standard library, one JSON row per
   session, as above. *Alternative:* one JSON file per session (simpler, no schema, but no
   transactions and awkward to list or purge later).
2. **CLI resume.** *Recommended:* `customer-support-chat --session <id>` resumes that
   session, `--resume` resumes the most recent unfinished one, and a bare run starts a new
   session and prints its id. Nothing resumes implicitly. *Alternative:* a bare run resumes
   the latest unfinished session, with `--new` to start fresh; friendlier, but it surprises
   anyone who expects a clean start.
3. **Finished conversations.** *Recommended:* resuming one shows the saved transcript and
   says the conversation ended, and the user starts a new one. *Alternative:* start a fresh
   conversation silently under the same id.
4. **Retention.** *Recommended:* keep sessions until deleted by hand, keep the database out
   of git, and record the privacy note above for Phase 10. *Alternative:* purge sessions
   older than N days on startup, which needs a setting and a test and is a step toward the
   session management the sprint says to avoid.
