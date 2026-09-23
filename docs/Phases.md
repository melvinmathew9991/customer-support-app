# Phases — Customer Support App

This project doesn't fit a generic "login → dashboard" phase template: it's
a conversational agent, not a CRUD app, and the core flow is already built.
Phases below reflect that — the early phases are marked **Done** to record
what already exists (so future work doesn't re-litigate it), and later
phases are the actual next steps.

## Phase 1 — Core graph framework ✅ Done
- `graph/` Node/Edge abstractions (`BaseNode`, `BaseEdge`,
  `ChainBasedNode`/`Edge`, `TextBasedEdge`, `StaticTextNode`).
- `domain/` models: `MessageHistory`, `Role`, `MessageOutput`, `EdgeOutput`.
- Unit tests for graph control flow independent of any LLM.

## Phase 2 — Identification flow ✅ Done
- `GreetingNode` asks for email/phone.
- `UserInfoChainBasedEdge` (tool-calling agent) resolves the user via
  `tools/user_info_db.py` into a structured `UserProfile`.
- **Bugfix (2026-09-18, found via Sprint 1's first golden-set run - see
  `docs/eval/Baseline-2026-09-18.md`):** identification previously accepted
  non-identifying input (e.g. "hey there") or an unmatched email/phone and
  fabricated a schema-valid `UserProfile` instead of failing - a silent
  identity bypass. `UserInfoChainBasedEdge._parse` now deterministically
  checks the raw tool-call observations before extraction, and
  `AuthenticatedUserNode` fails safe instead of crashing if a non-`UserProfile`
  ever reaches it.
- **Bugfix (2026-09-19, found via the scaled 38-entry golden-set run - see
  `docs/eval/Baseline-2026-09-19.md`):** a sharper variant of the above
  slipped past that first fix - given input as unrelated as "what's up",
  the tool-calling agent called `user_info_db_search` with a fabricated
  argument ("john@doe.com") that happened to match a *real* account,
  authenticating the conversation as that person despite the user never
  providing any identifying information. The first fix only checked that
  the DB lookup returned *something*, not that its argument came from the
  user's own message. `UserInfoChainBasedEdge._parse` now also requires
  the looked-up value to actually appear in the user's latest message
  before trusting the match. Verified: the exploit sequence now correctly
  fails safe, and happy-path identification still works.
- **Bugfix (2026-09-20, #29, found via the larger-model experiment - see
  `docs/eval/Model-Experiment-Results-2026-09-20.md`):** the guards only
  rejected an *empty* subscription result, not a subscription lookup that never
  ran. `llama3.1:8b` writes its second tool call out as text instead of calling
  it, and the extractor then invented the tier ("free" for premium users), so
  premium users were served the free KB. `UserInfoChainBasedEdge._parse` now
  requires the subscription lookup to have run, takes `subscription` from the DB
  record rather than the extractor, and rejects a record that belongs to a
  different user. Behavior change: a model that skips the call now fails safe at
  the greeting instead of silently assigning a tier. The 3B is unaffected: every
  `ident-*` entry that completes still passes and `ident-005/013` still fail safe
  (`ident-011` hangs on the 3B on unmodified `main` too: the model generates to
  the context limit with no stop token, tracked in #30; unrelated to this change).
- **Lookup (2026-09-20, #11, found in the Sprint 2 audit - see
  `docs/eval/Sprint2-Audit-2026-09-20.md`):** the greeting asks for an email or phone
  number, but `search_user_info_on_db` compared the email string exactly, so a phone
  number could never identify anyone and a differently-cased email failed too. It now
  matches an email ignoring case and surrounding space, or a phone number by its digits
  (6 or more, spacing and punctuation ignored); anything else matches nobody. The guard
  that requires the looked-up value to appear in the user's own message compares digits
  for phone numbers. Behavior change: phone and mixed-case email identification now
  succeed instead of failing safe; `ident-007` and `ident-010` are scored entries.
- **Failed identification (2026-09-21, #37, found while designing Sprint 3):** after the
  identity edge ran out of retries the bot said it "couldn't verify your account" and then
  kept answering from the free KB, contradicting the PRD. The maintainer chose to end the
  conversation at that message: `AuthenticatedUserNode.is_node_final()` is true whenever the
  node holds no `UserProfile`, so the pipeline reports the conversation over and the CLI and
  app stop. Behavior change: an unidentified user is no longer answered. Golden-set entry
  `ident-014` sends a question after the failure and fails on the old code.

## Phase 3 — Tiered RAG support answers ✅ Done
- `AuthenticatedUserNode` (`RetrievalNode`) answers from Chroma, retriever
  chosen deterministically by `UserProfile.subscription` (free vs. paid).
- `tools/rag_responder.py` (`HelpCenterAgent`) builds/loads both
  collections from `assets/free` and `assets/paid`.
- **Bugfix (2026-09-18):** `HelpCenterAgent` was calling
  `Chroma.from_documents` unconditionally on every instantiation (every
  process start/session), re-embedding and re-inserting the KB with no
  id-based dedup - duplicate chunks accumulated on disk on every restart,
  degrading retrieval. Now reuses the persisted collection if it's already
  populated, and only reindexes when it's empty. `chroma_db/` was reset to
  clear the duplication that had already accumulated.
- **Reindex command (2026-09-19, Sprint 2):** `scripts/reindex_kb.py`
  rebuilds the indexes from `assets/` (`--tier`, `--check`), so KB edits no
  longer mean deleting `chroma_db/` by hand. Chunks now get stable ids
  (`<file>#<n>`, files in sorted order). `HelpCenterAgent.index_status()`
  compares the persisted index with `assets/` by content, and the app logs a
  warning at startup naming any stale tier instead of silently serving the old
  KB.
- **KB content (2026-09-19, Sprint 2):** `assets/free/locations.txt`,
  `assets/free/pos.txt` and `assets/paid/locations.txt` rewritten so each tier's
  limit is stated unambiguously (the free `pos.txt` previously contradicted
  itself, and the "depends on your plan" sentence gave evasive answers); see
  `docs/eval/KB-Rewrite-Results-2026-09-19.md`.
- **Invented-steps guard (2026-09-19, Sprint 2):** `RetrievalNode._predict`
  now replaces an answer with the not-covered reply when it uses navigation
  wording (click, navigate, tap, "A > B") that the retrieved context does not; the
  turn log records `invented_steps_blocked`. Prompt rule 5 asks the model not to
  invent menu paths or steps. `assets/free/payments.txt` no longer contradicts
  itself on manual payments. See `docs/eval/Fix-16-17-Verification-2026-09-19.md`.
  Heuristic: it does not catch fabricated steps written in plain prose.
- **Answer prompt (2026-09-19, Sprint 2):** `RetrievalNode._SYSTEM_PROMPT` is
  now stricter (answer only from context, state applicable limits, exact
  "I don't have information about that in our help center." when uncovered,
  no invented contact channels); see `docs/eval/Prompt-Experiment-2026-09-19.md`.

## Phase 4 — Call-me / ticketing flow ✅ Done
- `CallCustomerEdge` detects a callback request and extracts the phone
  number into a `PhoneCallRequest`.
- `CallCustomerNode` produces a `PhoneCallTicket` and a closing message;
  optional Whisper transcription via `tools/audio_transcribe.py`.
- **Bugfixes (2026-09-19, found by the Sprint 1 eval harness):**
  - Without the optional `audio` extra the node crashed with
    `ModuleNotFoundError: whisper`. `tools/audio_transcribe.py` now exposes
    `transcription_available()`; when it's false `CallCustomerNode` skips the
    LLM/tool call and replies that the callback was logged, with no ticket
    summary (none can be produced without a call to transcribe).
  - Callback detection missed 2 of 7 genuine requests (71% recall). Root
    cause: `PydanticTextBasedEdge.check()` passed the whole message history to
    the intent classifier, including the internal
    `system: User Info retrieved: ... phone=...` line, which deterministically
    biased `llama3.2:3b` toward "no" for some phrasings. `check()` now passes
    only user/assistant messages. Removing that line alone made the classifier
    over-fire on phone-related questions, and prompt rewording only traded
    misses for false triggers, so `CallCustomerEdge.check()` also requires a
    phone number (6+ digits) in the user's latest message before the LLM
    intent check runs. **Behavior change:** a bare "call me" with no number no
    longer triggers a callback.
- **With-audio path exercised (2026-09-21, #10; `llama3.2:3b`, torch in a short-path venv),
  found broken and then fixed (#43, #44).** Whisper was fine from the start: the 55.5 s sample
  transcribed in 19 s on CPU (`base` model) and the transcript is accurate. The ticket step
  failed: asked for as free text with the schema in the prompt, the model returned the
  `PhoneCallTicket` JSON *schema* instead of a ticket (identical on two runs at temperature
  0), and the uncaught parse error crashed the callback turn (#43). The fix asks for the
  ticket with structured output, as the identification chain does, and
  `CallCustomerNode.greeting_message()` falls back to the "callback logged" reply if a ticket
  still cannot be read, so a bad ticket never ends the conversation. The first structured
  version cut `call_summary` down to its first clause (identical on two runs); telling the
  prompt to keep the whole summary fixed that. A fresh-venv install of the extra had failed
  on `pkg_resources` in the `openai-whisper==20231106` build (#44); the extra now pins
  `20250625`, which builds, and `pip install -e ".[audio]"` needs no workaround. Live
  after the fix: the callback turn returns a ticket for agent Ruby and customer Michael
  whose summary matches the call (report §10.6). The tool always transcribes the same fixed
  recording, so every ticket describes that call whoever asked. Without the extra the
  callback path works as described above.
- **Decision (2026-09-19, #7): keep it.** A callback request with no phone
  number still gets a normal answer, not a callback. Rejected for now:
  - *Use the number on the user's profile.* It calls a number the user did not
    type, the behavior #22 removed (extraction now always returns a number from
    the user's own message), and an earlier draft false-triggered `rag-oos-002`.
  - *Ask "what number should we call?"* It needs the intent check to judge "wants
    a call" with no digit pre-check to protect it, and that judgment is unreliable
    on the 3B model (3 of 6 hard negatives with a number false-triggered, #23).
    Revisit after #23 improves intent precision, with golden-set entries for the
    no-number phrasings, a full eval re-run, recall >=90% and precision >=95%.

- **Negation (2026-09-20, Sprint 2 audit):** `_DO_NOT_CALL_RE` also vetoes "no need to
  call/phone/ring" and "no need for (you to|a) call", which the plain-request pattern
  used to accept ("No need to call me back, my number is ..."). A message that declines
  and requests in one sentence ("Never call me before 9am, but do call me on ...") was
  vetoed whole; fixed in #33 (2026-09-21): each decline is now taken out of the message
  before a request is looked for, so a separate request beside it still counts. Trade-off:
  a decline followed by a conditional offer ("call me back only if the email bounces")
  now counts too (`call-070`); see `docs/eval/Callback-Compound-Results-2026-09-21.md`.

## Phase 5 — Interfaces ✅ Done
- Streamlit `app.py` (Chat + Graph tabs, live DAG rendering via
  `ui/graph_renderer.py`).
- CLI (`cli.py`, `customer-support-chat` console script).
- Provider abstraction (`config.py`): Ollama by default, OpenAI opt-in, for
  both chat model and embeddings.
- **CLI exit (2026-09-20, #12):** `customer-support-chat` ends cleanly with "Goodbye." and
  exit code 0 when stdin ends (piped input, Ctrl+D or Ctrl+Z) or the user types `quit` or
  `exit`; before, it died with an `EOFError` traceback.
- **Telemetry noise (2026-09-20, #13):** the `ANONYMIZED_TELEMETRY=False` setting worked,
  but chromadb 0.5.x calls `posthog.capture` positionally while `posthog` 6+ takes only
  `capture(event, **kwargs)`, so every client start logged "Failed to send telemetry event"
  at ERROR anyway. `config.py` now drops that one message from that one logger (nothing is
  being sent) and its comment says why; other errors from the logger still show.
- **Bounded LLM calls (2026-09-20, #30):** `LLM_MAX_TOKENS` (default 1024) and
  `LLM_TIMEOUT_SECONDS` (default 120) apply to both providers. A timeout inside a turn
  becomes "Sorry, that took too long to answer. Please try again." (turn log field
  `timed_out`), and the conversation stays on the same node. Before this, a 3B model that
  never emitted a stop token hung the turn indefinitely (`ident-011`). The OpenAI path is
  configured the same way but has not been exercised.

## Phase 6 — Session persistence ✅ Done
Design: `docs/Persistence-Design.md`. The storage decision `Rules.md` asks to be scoped
first was made explicitly (SQLite through the standard library, one JSON row per session;
no new dependency, no ORM).
- `session_store.py`: `SessionStore` saves one row per conversation (message history,
  current node name, the node's typed input, the two edges' retry counters, conversation id,
  whether it ended), rewritten whole in a transaction. The schema is versioned with
  `PRAGMA user_version` and built by an append-only list of migrations. An unreadable row
  logs a warning and is treated as missing; a database from a newer schema raises
  `SessionStoreError` when opened.
- `CustomerSupportPipeline(store=None, session_id=None)`: with a store it saves after every
  completed turn (including a timed-out one), and given a session id the store holds it
  rebuilds the graph and restores the state; nothing is replayed and no model is called.
  With no store it behaves exactly as before, which is why the eval harness and the existing
  tests are unaffected. A session that cannot be resumed (unknown node, wrong input type,
  bad counters, or a failed identification) starts a new conversation with a warning. A
  failed save costs resumability, not the turn; a crash mid-turn saves nothing from it.
- CLI: `--session ID`, `--resume`; nothing resumes implicitly. Streamlit: the id is kept in
  the URL (`?session=<id>`); an ended conversation shows its transcript, disables input and
  offers a button to start again.
- `SESSION_DB_PATH` setting (default `data/sessions.sqlite`, gitignored).
- Known: saved sessions hold PII in the clear, and the Streamlit session id in the URL is a
  bearer token; both are for Phase 10 to revisit. (After three unidentifiable messages the
  bot used to keep answering from the free KB; that ended with the fix for #37, described
  under Phase 2.)

## Phase 7 — Real user store ✅ Done (Sprint 4, `docs/User-Store-Design.md`)
- The mock `tools/user_info_db.py` is replaced by `tools/user_store.py`: a `UserStore`
  Protocol, a `MockUserStore` (today's in-memory fixture, unchanged, default for tests),
  and a `SqliteUserStore` (real, persistent, auto-seeded from the same fixture data on
  first open - no separate seed step). `agents/support.py`'s `UserInfoChainBasedEdge`
  takes a `user_store` and builds its two tools from it; nothing about the edge's
  identification logic changed. `Settings.user_store_provider` (default `sqlite`) picks the
  backend - a config change, not a code change in `agents/`, as the phase asked for.
- Identification is still a lookup, not authentication: anyone who knows a customer's
  email or phone number is served that customer's tier. Decided, not just deferred: a
  second factor is out of scope for this sprint (`docs/User-Store-Design.md` decision 2) -
  that stays a stated non-goal in `PRD.md`, unchanged from before.

## Phase 8 — Evaluation harness for LLM-dependent behavior ✅ Done (Sprint 5, `docs/Eval-Gate-Design.md`)
- **Built (Sprints 1-2, grown since):** a 135-conversation golden set (122 at the end of
  Sprint 3; `ident-014` was added for #37 and `call-059`..`070` for #33)
  (`tests/eval/golden_set.json`), an automated scoring harness
  (`tests/eval/run_eval.py`), metric definitions and targets
  (`docs/eval/Metrics.md`), and the structured per-turn log it scores from.
  The full run still stays manual (135 entries against a live Ollama model, a
  pre-merge PR-template checklist item); the deterministic scoring logic is
  unit-tested and runs in CI.
- **Built (Sprint 5):** a CI-enforced regression gate (`scripts/eval_gate.py`, a new
  `eval-gate` job in `.github/workflows/ci.yml`) - a small, fixed 14-entry subset runs
  against a real, GitHub-hosted Ollama on every PR, and fails if any entry that wasn't
  failing starts failing against a committed baseline. Proven for real on live GitHub
  Actions, not simulated: a deliberate tier-scoping break made the job fail as designed.
  **Known gap, not yet closed:** the check isn't marked *required* in GitHub's branch
  protection settings, so CI failing doesn't yet block a merge by itself - found the hard
  way when a disposable "do not merge" proof PR was merged anyway and had to be hotfixed
  (`docs/Sprints.md`'s Sprint 5 section has the full account). Still open: per-metric
  regression thresholds beyond the entry-level check (deliberately not built - see
  `Eval-Gate-Design.md` for why they'd be redundant on a fixed subset), and the required-check
  setting itself.

## Phase 9 — UI/design polish ✅ Done (Sprint 6, `docs/Design.md`)
- `.streamlit/config.toml` applies the Design.md §2 palette (one static custom theme -
  Streamlit 1.39's `[theme]` section has no way to express a separate dark-mode
  palette; a viewer's manual dark-mode toggle gets Streamlit's own dark defaults, not
  Design.md's dark column).
- `app.py`: `st.title` moved from brand copy to a plain "Support" heading (§3); a
  subscription-tier badge (`st.caption`) once `AuthenticatedUserNode` holds a
  `UserProfile` (via the new `CustomerSupportPipeline.current_user_profile`
  property); retry prompts render as `st.warning`, ticket-confirmation messages as
  `st.success` (§4), using the existing graph-layer retry vocabulary
  (`GreetingNode.RETRY_PROMPT`) and node identity rather than new UI-side heuristics.
  The Graph tab is untouched, as specified.
- Each saved assistant reply records the node its turn ended at, so a resumed session
  styles its ticket confirmations too (closed 2026-09-23; sessions saved before then
  replay them as plain text). Checked rendered in headless Edge in both themes, all
  text at WCAG AA or better (`docs/Sprints.md`, Sprint 6 closeout).

## Phase 10 — Deployment & observability
- Containerize / document a deployment path for the Streamlit app.
- Metrics beyond what exists (a structured per-turn JSON-line log,
  `logs/turns.jsonl`, was added in Sprint 1 for the eval harness), such as
  aggregation, alerting and token/cost tracking, if this moves beyond local use.

## Working agreement
- Don't start a later phase's scope inside an earlier one's PR/change —
  keep changes traceable to the phase they belong to.
- When a phase is completed, flip its checkbox/status in this file in the
  same change, so this file stays the single source of truth for "what's
  done" without needing to re-read the whole codebase.
