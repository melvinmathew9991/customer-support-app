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

## Phase 5 — Interfaces ✅ Done
- Streamlit `app.py` (Chat + Graph tabs, live DAG rendering via
  `ui/graph_renderer.py`).
- CLI (`cli.py`, `customer-support-chat` console script).
- Provider abstraction (`config.py`): Ollama by default, OpenAI opt-in, for
  both chat model and embeddings.

## Phase 6 — Session persistence (next)
- Persist `MessageHistory` + current node across process restarts (not just
  `st.session_state`), so a user can resume a conversation.
- Decide on a storage backend (file-based for local dev vs. a real DB) —
  this is the "add a real datastore" decision flagged in `Rules.md`, so
  scope it explicitly before starting.

## Phase 7 — Real user store
- Replace the mock `tools/user_info_db.py` with a real lookup (API or DB),
  behind the same function signatures so `agents/support.py` doesn't change.

## Phase 8 — Evaluation harness for LLM-dependent behavior
- Today, tool-calling/RAG/structured-extraction correctness is verified
  manually against Ollama (per the README). Build a lightweight, repeatable
  eval (fixed transcripts + assertions) to catch regressions when prompts,
  models, or the graph change, without making CI depend on a live model.

## Phase 9 — UI/design polish
- Apply `Design.md` (theme, typography, chat styling) to `app.py` — today
  it's an unstyled default Streamlit app (bare `st.title` + chat tabs).

## Phase 10 — Deployment & observability
- Containerize / document a deployment path for the Streamlit app.
- Structured logging/metrics beyond `logging_config.py`'s current console
  logging, if this moves beyond local use.

## Working agreement
- Don't start a later phase's scope inside an earlier one's PR/change —
  keep changes traceable to the phase they belong to.
- When a phase is completed, flip its checkbox/status in this file in the
  same change, so this file stays the single source of truth for "what's
  done" without needing to re-read the whole codebase.
