# Graph-Orchestrated LLM Customer Support Agent — Project Report

**Repository:** melvinmathew9991/customer-support-app (`main`, with every sprint and fix branch merged and kept)
**Stack (this verification, project `.venv`):** Python 3.10.10 · Streamlit 1.39.0 · LangChain 0.3.7 (+ langchain-community 0.3.7, -ollama 0.2.0, -openai 0.2.6, -chroma 0.1.4, -text-splitters 0.3.2) · ChromaDB 0.5.20 · pydantic 2.9.2 / pydantic-settings 2.6.1 · graphviz 0.20.3 · pytest 8.3.3 · ruff 0.7.4 · posthog 7.57.0 (transitive, unpinned) · Ollama with `llama3.2:3b` (chat, default), `nomic-embed-text` (embeddings) and `llama3.1:8b` (tested, not adopted); OpenAI's `gpt-4o-mini` exercised as the opt-in chat provider for the first time this update (§10.10; embeddings stayed on local Ollama). Not installed in the project `.venv`: `openai-whisper`, `sentence-transformers` (Whisper and torch 2.14.0 were installed once in a separate short-path venv to exercise the audio path, §10.6). The dependency pins are unchanged since the initial commit; the only later edits to `pyproject.toml` are the ruff `extend-exclude` for the legacy notebook (#34).
**Status:** Sprints 1-6 are complete and merged - every sprint `docs/Sprints.md` planned is now done, leaving only Sprint 7 (deployment & observability) unscheduled. The graph-orchestrated agent works end to end and was re-exercised live on `main` for this update (identification by email and by phone against the real store, tier-scoped answers, a callback, a fail-safe that ends the conversation, a save-and-resume through the session store; §10.2). 513 unit tests across 20 files pass and lint is clean. **Sprint 4 (Phase 7) replaced the mock, in-memory user "database" with a real, persistent one** (`tools/user_store.py`'s `SqliteUserStore`, auto-seeded, a config change not a code change in `agents/`; `docs/User-Store-Design.md`). **Sprint 5 (Phase 8) added a CI-enforced regression gate** (`scripts/eval_gate.py`, a new `eval-gate` job in CI running 14 curated golden-set entries against a real, GitHub-hosted Ollama on every PR; `docs/Eval-Gate-Design.md`) - proven for real: a deliberate tier-scoping break on a disposable branch made the gate fail exactly as designed, and that same proof also caught a real incident (the disposable proof PR itself got merged to `main` because the check wasn't yet *required*; caught within minutes, reverted, and both `test`/`eval-gate` are required status checks since 2026-09-22 - `docs/Sprints.md`'s Sprint 5 section has the full account). **A real, measured comparison against OpenAI followed** (no token accounting existed before this update - a new `TokenUsageCallbackHandler` logs exact input/output tokens per LLM call for both providers): `gpt-4o-mini` matched `llama3.2:3b` on every machine-scored metric and *closed* the one metric Sprint 2 carried as an accepted known limit (callback precision, 94%→98% on the same 135-entry golden set), at a measured cost of $0.03 for the full run (§10.10). **Sprint 6 (Phase 9) applied `docs/Design.md`'s theme to `app.py` for the first time** - a `.streamlit/config.toml` palette, a subscription-tier badge, and retry/ticket-confirmation message styling, with a full golden-set regression showing 0 of 135 entries changed result, and its two open items closed on 2026-09-23: resumed sessions now keep ticket-confirmation styling, and the theme was checked rendered in a real browser engine in both modes, all text at WCAG AA (§10.11). **`docs/eval/` (46 report files) is no longer tracked in git going forward** - it had been committed as a deliverable every sprint through Sprint 5, but kept growing every run; existing reports stay on disk and in history, only future changes stop being picked up (`docs/Sprints.md`). **The sample data is original since 2026-09-23 (#14):** the Shopify-derived knowledge base and the call of unknown origin were replaced by a knowledge base for a fictional platform, Brightstall, and a synthesized call, so the whole repository is MIT; every machine-scored metric held except one borderline callback entry (§10.12). **Accuracy targets on fresh held-out cohorts (2026-09-23, §10.13):** invented steps 0 of 22 (#17, met); callback precision 100% (met) but recall 80% vs ≥90% (#23, not met); hallucination 4.5% or 9.1% depending on one judgment call vs ≤5% (#5, met only on the lenient reading). A second round (§10.14) missed all three #5/#23 targets on new unseen questions (recall 77%, precision 91%, hallucination 10%) while raising round-1 recall to 93%. The larger local model was tried earlier and did not help. A process evaluation (`docs/Process-Evaluation.md`) rated the method strong and the statistics weak; its plan is proposed, not adopted.
**Timeline:** 2026-09-18 → 2026-09-23, single contributor (Melvin Mathew). Sprint 4 (#51, Phase 7), Sprint 5 (#52, Phase 8, plus hotfix #55) and Sprint 6 (#58, Phase 9, plus the token-usage/OpenAI-comparison work) all merged 2026-09-22. Pre-Sprint-1 (MVP baseline + out-of-band fixes) → Sprint 1 (evaluation foundation) → git workflow tooling → Sprint 2 (KB/retrieval hardening) → audit fixes → Sprint 3 (session persistence) → post-Sprint-3 fixes (#37, #33, the with-audio path) → variance measurement (#50) and the license decision (#49) → Sprint 4, real user store (#51, Phase 7) → Sprint 5, CI regression gate (#52, Phase 8) → hotfix for the merge incident above (#55) → docs closeout (#56, #57) → token-usage logging, the OpenAI comparison, and Sprint 6, UI polish (#58, Phase 9) → 2026-09-23: Sprint 6 closeout (#59), the synthetic knowledge base replacing the third-party sample data (#60, closes #14), quality round 1 on fresh held-out cohorts (#61, closes #17), a save-time tie bug behind a flaky test (#62), and quality round 2 for #5 and #23 (#63, targets not met).

**Update cadence:** this file is updated in the same pull request as any change that alters something it states (counts, architecture, behavior, metrics, findings, limitations), and re-verified against the repository at the end of each sprint (see `docs/Sprints.md`'s cross-cutting rules), so it reflects the project's current state rather than a point-in-time snapshot. Counts that name a pull request ("as of #N") describe the repository at that merge.

---

## 1. Overview & Purpose

A LangChain customer support agent whose conversation flow is modeled as an explicit graph (`Node`/`Edge` framework in `graph/`) instead of a freeform agent, so behavior at each stage is constrained and predictable: `GreetingNode` (identify the user) → `AuthenticatedUserNode` (answer from a tier-selected RAG knowledge base) → `CallCustomerNode` (detect and route callback requests into a ticket). Runs fully local by default via Ollama — no API key required; OpenAI is available as an opt-in and was exercised for the first time this update, matching or beating the local model on every measured metric (§10.10). Conversations are saved after every turn, so a closed terminal or a reloaded page resumes where it stopped.

The product itself (Phases 1-5) was already built and unit-tested when this engagement began. The work covered here is what came after: running it end-to-end outside its original development context, building the evaluation infrastructure Sprint 0's retrospective had flagged as the project's one real gap (Sprint 1), using that infrastructure to fix the failures it exposed and to test, honestly, which of them a larger model would remove (Sprint 2), adding session persistence (Sprint 3), replacing the mock user store with a real one (Sprint 4), turning the eval harness into an enforced CI gate (Sprint 5), measuring a real alternative backend against the shipped one (the OpenAI comparison), and applying the UI/theme spec that had existed since early on but was never picked up (Sprint 6) - completing every sprint this project ever planned except deployment and observability (Sprint 7).

## 2. Use Case & Objectives

Primary use case: a tiered (free/paid) e-commerce support chatbot that identifies a customer, answers from a knowledge base scoped strictly to their subscription tier, and can hand off to a human callback when asked — while being *provably* measurable, not just demoable.

Objectives, as they currently stand:

- Identify a user from a natural-language email/phone message and resolve their subscription tier — done. Three fabrication or bypass bugs were found and fixed along the way (§13 findings 6, 7, 20). Phone numbers and mixed-case emails identify correctly since the audit fix (#11); before it, the greeting asked for a phone number the lookup could not use. A user who still cannot be identified after three tries is told so and the conversation ends (#37); before, they were answered from the free KB.
- Answer support questions grounded only in the user's own tier's knowledge base, with zero cross-tier leakage — done for leakage (0% on 39 scored retrieval cases). **Grounding is not at target:** see the hallucination row below.
- Detect callback requests and route them to a ticketing flow — working, with a caveat that changed in Sprint 2: recall is 100% (44/44) and precision 93.6% (44/47) on the full set, but on a 22-entry cohort held out from design, precision is **83%** (target ≥95%). Since #33 a request that sits beside a decline in the same message counts, at the price of one new false trigger (`call-070`). A callback request must include a phone number (a maintainer decision, #7), and the ticket has a transcript-based summary only if the optional `audio` extra is installed (with it, the path was broken when first exercised, #43 and #44, and is fixed, §10.6).
- Run entirely on a local, free model stack — done (Ollama). A larger local model (`llama3.1:8b`) was tested and rejected (§10.5).
- Keep a conversation across a restart — done (Sprint 3): saved per turn in a local SQLite file, resumed by session id from the terminal or the page URL.
- Make the system's behavior measurable, not just observable — done: every defined metric has a real number (machine-scored on a 135-entry golden set; hallucination hand-graded). The hallucination rate misses its ≤5% target, and several targets are too strict to confirm at the sample sizes used (§13 finding 28).

## 3. Proposed Solution

A single installable package (`src/customer_support_app/`) plus a thin CLI/Streamlit front end — no service layer, no separate database beyond the embedded Chroma store and a local SQLite file for saved conversations, no orchestration framework beyond LangChain itself and this project's own small `Node`/`Edge` abstraction.

`graph/` is the reusable control-flow framework (any project could reuse it); `agents/support.py` is the concrete conversation built on top of it; `tools/` wraps the user store (real by default since Sprint 4, a mock kept for tests), the RAG retriever build/reuse logic, and call transcription; `session_store.py` and `pipeline.py` save and resume a conversation; `tests/eval/` is the evaluation harness, sitting alongside the original `tests/` unit suite rather than replacing it. `scripts/reindex_kb.py` rebuilds the knowledge-base index deterministically; `scripts/eval_gate.py` (Sprint 5) is the CI regression gate.

## 4. Project Architecture

| Layer | Module | Lines | Responsibility |
|---|---|---|---|
| Config | `config.py` | 162 | pydantic-settings `Settings`: LLM/embeddings provider, paths, `turn_log_path`, `llm_max_tokens` and `llm_timeout_seconds` (#30), `session_db_path` (Sprint 3); drops chromadb's false "Failed to send telemetry event" error (#13); `get_chat_model()` attaches a `TokenUsageCallbackHandler` to both providers (this update) |
| Logging | `logging_config.py` | 112 | Console logger + structured JSON-line turn logger (`logs/turns.jsonl`); `TokenUsageCallbackHandler` logs one `llm_usage` event (input/output tokens) per LLM call, for either provider (this update) |
| Persistence | `session_store.py` | 161 | `SessionStore`: SQLite (standard library), one JSON row per conversation, versioned schema with an append-only migration list; unreadable rows are a warning and a miss, a newer schema raises `SessionStoreError` |
| Domain | `domain/chat.py` | 63 | `MessageHistory`, `Role`, `model_input()` |
| Domain | `domain/graph.py` | 25 | `MessageOutput`, `EdgeOutput` |
| Domain | `domain/validation.py` | 28 | `UserProfile`, `PhoneCallRequest`, `PhoneCallTicket`, `Validation` |
| Graph framework | `graph/node.py` | 67 | `BaseNode`: `run_to_continue`, `execute` |
| Graph framework | `graph/edge.py` | 89 | `BaseEdge`: parse/retry/exhaustion lifecycle |
| Graph framework | `graph/chain_based_node.py` | 188 | `RetrievalNode` (RAG, strict answer prompt, `invents_steps()` guard, retrieval logging), `MultifunctionNode` |
| Graph framework | `graph/chain_based_edge.py` | 157 | `ZeroShotChainBasedEdge` (tool-calling agent; exposes raw intermediate tool-call steps) |
| Graph framework | `graph/text_based_edge.py` | 91 | `PydanticTextBasedEdge` (condition-check + structured extraction; system messages excluded from both) |
| Graph framework | `graph/static_text_node.py` | 30 | Fixed-text node |
| Agents | `agents/support.py` | 430 | `GreetingNode`, `UserInfoChainBasedEdge` (identity guards, tier taken from the DB record), `AuthenticatedUserNode` (final, so the conversation ends, when identification failed, #37), `CallCustomerEdge` (digit pre-check, do-not-call phrasings taken out before a request is looked for #33, explicit-request patterns, typed-number check) / `CallCustomerNode` |
| Tools | `tools/user_store.py` | ~150 | `UserStore` protocol; `MockUserStore` (in-memory, test default) and `SqliteUserStore` (real, persistent, auto-seeded, default since Sprint 4); email lookup ignores case, phone lookup by digits, #11 |
| Tools | `tools/rag_responder.py` | 161 | `HelpCenterAgent`: idempotent index, stable chunk ids, content-based staleness check |
| Tools | `tools/audio_transcribe.py` | 48 | Whisper-based call transcription; the ticket is asked for with structured output (#43); `transcription_available()` lets callers degrade instead of crashing |
| Pipeline | `pipeline.py` | 280 | `CustomerSupportPipeline` orchestration + per-turn structured logging; a model timeout becomes a reply (#30); with a `SessionStore` it saves after every completed turn and can resume a saved conversation by rebuilding the graph (no replay, no model call); `current_user_profile` property backs the Sprint 6 tier badge; each saved reply records the node its turn ended at (Sprint 6 closeout) |
| Interfaces | `cli.py` | 104 | Terminal chat entrypoint; exits cleanly on end of input or `quit`/`exit` (#12); `--session ID` and `--resume` pick up a saved conversation, nothing resumes implicitly |
| Interfaces | `app.py` | 157 | Streamlit Chat + Graph tabs; the session id lives in the URL (`?session=<id>`), so a reload or server restart resumes; an ended conversation shows its transcript and a start-again button. Themed since Sprint 6: a subscription-tier badge, `st.warning`/`st.success` for retry/ticket-confirmation messages (§10.11) |
| UI | `ui/graph_renderer.py` | 55 | Graphviz DAG rendering |
| Theme | `.streamlit/config.toml` | 12 | `Design.md`'s light palette (Sprint 6); Streamlit 1.39 supports one static custom theme, so a viewer's dark-mode toggle gets Streamlit's own dark defaults, not a second custom palette (§10.11) |
| Scripts | `scripts/reindex_kb.py`, `scripts/eval_gate.py`, `scripts/summarize_eval_runs.py` | 59, ~180, ~130 | Rebuild the Chroma index from `assets/` (`--tier`, `--check`); the CI regression gate (Sprint 5); compare several full eval reports for run-to-run variance |
| Tests | `tests/**/test_*.py` | 3,327 | 513 tests across 20 files, none needing a live model: agents (`test_call_customer_edge` 64, `test_user_info_edge` 9, `test_call_customer_node` 4, `test_authenticated_user_node` 2), domain (`test_chat` 4), graph (`test_retrieval_guard` 33, `test_node` 5, `test_text_based_edge` 3, `test_edge` 2), tools (`test_user_store` 35, `test_rag_responder` 8 - `test_user_info_db.py` was retired in Sprint 4 with the mock DB it tested), eval (`test_golden_set` 226, `test_run_eval_scoring` 19, `test_eval_gate` 10), and top level (`test_session_store` 23, `test_pipeline_persistence` 25, `test_cli` 14, `test_config` 12, `test_app_sessions` 14, `test_pipeline_timeout` 1) |
| Eval | `tests/eval/` | 452 (harness) | `golden_set.json` (135 hand-labeled conversations, 11 categories), `run_eval.py` (automated scoring harness), `ci_baseline.json` (Sprint 5), `README.md` (schema) |
| CI / tooling | `.github/workflows/ci.yml`, `scripts/eval_gate.py`, `.githooks/pre-commit`, `.github/pull_request_template.md` | ~180 (gate script) | pytest + `ruff check` blocking on every PR; a 14-entry live-model `eval-gate` job (Sprint 5), a required status check since 2026-09-22 (§10.9); local pre-commit test hook |
| Docs | `docs/*.md` (+ `docs/eval/*.md`, gitignored since this update) | — | PRD, Architecture, Rules, Phases, Design, Persistence-Design, User-Store-Design, Eval-Gate-Design, Process-Evaluation, Sprints, Git-Workflow, and 46 dated eval/experiment reports that stay on disk but are no longer tracked in git |

**2,552** total lines across `src/customer_support_app/`.

## 5. Folder Structure

```
.
├── README.md
├── .env.example / .env (gitignored) / .gitignore
├── pyproject.toml
├── .github/               # workflows/ci.yml, pull_request_template.md
├── .githooks/pre-commit   # runs pytest when src/, tests/ or pyproject.toml change
├── .streamlit/config.toml # tracked despite the directory's own blanket .gitignore rule (Sprint 6 - secrets.toml-style local config stays ignored)
├── docs/
│   ├── PRD.md, Architecture.md, Rules.md, Design.md, Git-Workflow.md, Process-Evaluation.md
│   ├── Persistence-Design.md, User-Store-Design.md, Eval-Gate-Design.md  # design-first docs per sprint
│   ├── Phases.md            # what's built, phase by phase, with dated bugfix notes
│   ├── Sprints.md           # the SDLC plan + live status of each sprint
│   ├── report.md            # this file
│   └── eval/                # Metrics.md + 46 dated baseline/held-out/audit/experiment reports -
│                             #   gitignored since this update (still on disk, no longer tracked)
├── scripts/reindex_kb.py, eval_gate.py, summarize_eval_runs.py
├── src/customer_support_app/
│   ├── config.py, logging_config.py, session_store.py, pipeline.py, cli.py, app.py
│   ├── agents/support.py
│   ├── domain/           # chat.py, graph.py, validation.py
│   ├── graph/             # the reusable Node/Edge framework
│   ├── tools/              # user_store.py, rag_responder.py, audio_transcribe.py
│   └── ui/graph_renderer.py
├── tests/                 # 513 unit tests (deterministic logic only)
│   └── eval/               # golden_set.json, run_eval.py, ci_baseline.json (Sprint 5), README.md
├── assets/                # free/ + paid/ knowledge base .txt files, sample call audio
├── notebooks/             # legacy exploratory prototype
├── logs/                  # gitignored - logs/turns.jsonl, structured per-turn output (incl. llm_usage events since this update)
├── data/                  # gitignored - sessions.sqlite, users.sqlite (Sprint 4), saved state (holds names, emails, phone numbers in the clear)
└── chroma_db/             # gitignored - persisted vector store
```

## 6. End-to-End Workflow

1. `GreetingNode` asks for an email/phone number.
2. `UserInfoChainBasedEdge` (tool-calling agent over a `UserStore` - `tools/user_store.py`, `SqliteUserStore` by default since Sprint 4) resolves a `UserProfile`. **Four guards must all pass before a match is trusted:** (a) the user lookup tool must have run and returned a non-empty result (an email, matched ignoring case, or a phone number, matched by digits, #11); (b) the value it was called with must appear in the user's own message, compared by digits for phone numbers (closes a bug where the model invented a lookup argument that matched a real account); (c) the subscription lookup must have run and returned a record (#29: without this, a model that skipped the call had its tier invented by the extractor); (d) the subscription is taken from the DB record itself, and that record must belong to the user who was identified, never from the extractor's reading of the findings. Any failure fails safe with a "couldn't verify your account" reply; once the retries run out (three failed attempts) that reply ends the conversation, because `AuthenticatedUserNode` is final when it holds no `UserProfile` (#37).
3. `AuthenticatedUserNode` (`RetrievalNode`) answers from Chroma, with the retriever chosen deterministically by `UserProfile.subscription`. The answer prompt requires the model to use only the retrieved context and to say the topic isn't covered otherwise; `invents_steps()` replaces an answer containing UI navigation wording absent from the retrieved context with the not-covered reply. `HelpCenterAgent` reuses a populated collection and warns at startup if the index is out of date with `assets/`.
4. Every LLM call is bounded (`LLM_MAX_TOKENS`, `LLM_TIMEOUT_SECONDS`); a timeout inside a turn becomes a "took too long, please try again" reply and the conversation stays on the same node (#30). Every turn emits a structured JSON-line record (`logs/turns.jsonl`) — node transitions, retrieved doc sources + similarity scores, tool calls made, latency — the raw material the eval harness scores against.
5. `CallCustomerEdge` decides whether the user asked to be called, in this order: no phone number (6+ digits) in the latest message → reject; every "don't call" or "no need to call" phrasing is taken out of the message and, if a plain request ("call me", "give me a call", "someone should phone", "callback") remains → accept, all without the model (#33: "never call me before 9am, but do call me on X" counts, "never call me on X" does not); a phrasing was taken out and no request remains → reject; otherwise the LLM intent check decides, shown only user/assistant messages, with a short condition that mentioning, giving, changing or asking about a number is not a request. The number it will call must appear in the user's own message; if the model mis-copies it and the message holds exactly one number, that number is used. If it fires, `CallCustomerNode` is meant to produce a ticket from a Whisper transcription when the optional `audio` extra is installed (the ticket is asked for with structured output, #43), and otherwise, or if the ticket cannot be read, replies that the callback was logged, with no ticket summary.
6. With a `SessionStore` (the CLI and the Streamlit app pass one), the conversation is saved after every completed turn: the message history, the current node's name and typed input, the retry counters of the identity and callback edges, and the conversation id. Given a session id the store holds, the pipeline rebuilds the graph, restores that state and skips the greeting; nothing is replayed and no model is called. A saved row that cannot be resumed (unknown node, wrong input type for its node, bad counters, or a failed identification) starts a new conversation with a warning. Without a store nothing changes, which is how the eval harness runs.

## 7. Technologies Used

| Category | Technology | Verified this update? |
|---|---|---|
| App runtime | Streamlit 1.39.0 | Now themed (`.streamlit/config.toml`, Sprint 6, §10.11); driven headlessly with Streamlit's `AppTest` in 15 unit tests plus a fresh-process resume check (Sprint 3), and rendered in headless Edge via Playwright in both themes for the Sprint 6 closeout (§10.11) |
| Orchestration | LangChain 0.3.7 (+ -community/-ollama/-openai/-chroma/-text-splitters) | Exercised live this update (§10.2) |
| Session store | SQLite (standard library `sqlite3`) | 22 store tests, including migration rollback and a newer-schema refusal; a save-and-resume check re-run live this update. No new dependency, no ORM |
| Vector store | ChromaDB 0.5.20 | Index checked against `assets/` this update: free 14 / paid 15 chunks, none stale |
| Chat model | Ollama `llama3.2:3b` (local, default) | Exercised live this update, and across the 135-entry golden set and every experiment |
| Chat model (tested, not adopted) | Ollama `llama3.1:8b` | Installed locally. Not re-run this update; results are from the Sprint 2 full run and targeted experiments (§10.5) |
| Embeddings | Ollama `nomic-embed-text` (local) | Exercised live this update (retrieval) |
| Chat model (opt-in) | OpenAI via `langchain-openai` (`gpt-4o-mini`) | Exercised live this update, full 135-entry golden set, first time an API key was configured (§10.10) |
| Audio/transcription | `openai-whisper` (optional `audio` extra) | **Not installed in the project `.venv`.** Installed in separate short-path venvs on 2026-09-21 (`openai-whisper` 20250625 pinned by the extra since #44, `librosa` 0.10.2, torch 2.14.0): Whisper works, the ticket step works (#43), and the extra installs in a fresh venv without a workaround; §10.6. The app degrades gracefully without it |
| Testing | pytest 8.3.3 | 446/446 pass (20 files, up from 335/19 - Sprint 6 added 7 tests, its closeout 3, the save-time fix #62 1, and the quality fixes and held-out cohorts 71) |
| Lint | ruff 0.7.4 | 0 findings on `src tests scripts` and on the whole repo, re-run this update; a blocking CI gate. `ruff format` is not enforced (20 files would change) |
| CI | GitHub Actions (`ci.yml`) | pytest + `ruff check src tests scripts`, both blocking on PRs and pushes to `main`; a live-model `eval-gate` job since Sprint 5 (PR-only), both `test` and `eval-gate` required status checks since 2026-09-22; 71 of 73 runs green (the 2 non-green are a deliberate proof failure and a superseded duplicate, not real breakage) |
| Version control | git + GitHub (`melvinmathew9991/customer-support-app`) | 136 commits, 38 merged PRs as of #58; merge commits, branches kept as history, tags `v0.1.0-sprint1` and `v0.1.0-sprint2` (`docs/Git-Workflow.md`); `main` requires a PR and the `test`/`eval-gate` checks |

## 8. Implementation Details

**Before Sprint 1 and in Sprint 1** (unchanged; details in `docs/Phases.md` and the Sprint 1 reports):

- **Environment repair:** the `.venv`'s editable install pointed at a stale path; `customer_support_app` failed to import at all until reinstalled.
- **RAG indexing made idempotent:** `HelpCenterAgent._create_index` re-embedded on every start (126/135 duplicate chunks, 12MB after repeated runs, versus 14/15 chunks and 7MB fresh).
- **Identification hardened against two fabrication bugs**, both found by building and running the golden set: garbage/unmatched input produced a schema-valid fabricated `UserProfile`, and a sharper variant let an unrelated message authenticate as a real user through an invented lookup argument.
- **Structured per-turn logging** and an **automated eval harness** (`tests/eval/run_eval.py`) built from scratch; three harness bugs found and fixed mid-way.
- **Whisper crash fixed** (degrades to an honest "callback logged" reply), and **callback recall root-caused** (an internal system message leaking into the intent classifier's prompt) and fixed with system-message exclusion plus a digit pre-check.

**Sprint 2:**

- **Triage before fixing** (`Triage-2026-09-19.md`): for all six problem answers from the Sprint 1 hallucination grade, the deciding KB sentence was in the top-ranked retrieved chunk. Retrieval and chunking were not the cause; the model ignored context it was given. This redirected the work from the retriever to the answer prompt and KB wording.
- **Answer prompt and KB rewrite:** a stricter "use only the context" prompt fixed an uncovered-question hallucination; rewriting `locations.txt` and `pos.txt` so each tier's limit is unambiguous fixed the self-contradiction (#6) and moved the hand-graded rate from 20% to 6.7% on the 15 entries it was tuned on. On 21 held-out questions the same code scored 9.5%, so the tuned number was optimistic.
- **#16 and #17:** the free `payments.txt` contradiction is fixed (#16, met). A prompt rule plus the deterministic `invents_steps()` guard removed click-path fabrications (#17), taking an untuned 15-entry cohort from 26.7% to 13.3% fabrication; two entries still fabricate in ways the guard cannot see. Not met.
- **Reindex tooling:** `scripts/reindex_kb.py`, stable chunk ids, a content-based staleness check and a startup warning.
- **Golden set 38 → 122**, growing by held-out entries written and committed before any run: 21 `rag-*`, 16 then 22 callback entries. A scorer that checks *which number* the bot says it will call.
- **Wrong-number callback fixed (#22):** the extraction prompt included the internal profile line, so `call-007` returned the profile number instead of the typed one in 5/5 runs. The fix excludes system messages from extraction and requires the extracted digits to appear in the user's message.
- **Callback precision (#23):** every stricter wording alone lost recall (11%, 82%, 52%, 48%); what kept it was a deterministic accept for plain requests and a "don't call" veto ahead of a shorter model condition. On the untouched cohort precision went 67% → 83%; not at target.
- **Callback behavior decision (#7):** a bare "call me" without a number does not trigger a callback; the digit pre-check stays.
- **Lint and CI (#9):** all 27 ruff findings fixed and verified behavior-neutral (syntax-tree comparison); `ruff check` is a blocking CI step.
- **Larger-model experiment:** `llama3.1:8b` vs `llama3.2:3b`, model only, with the criteria and decision rule committed before any run (§10.5). Not sufficient. It exposed a gap in the identity guard, fixed as **#29** (guard (c) and (d) above).
- **End-to-end audit and final fixes** (`docs/eval/Sprint2-Audit-2026-09-20.md`): the sprint's claims held and the live metrics reproduced. The audit found and fixed: a README that recommended the rejected 8B model; the lookup not supporting the phone numbers the greeting asks for (**#11**); no cap or timeout on LLM calls (**#30**); a "no need to call me" phrasing that started a callback; a swallowed exception in the retrieval log; and stale docs. It left open the license (#14, a legal decision) and a compound-phrasing callback case (**#33**). Two older small bugs followed in a separate PR: the CLI `EOFError` (**#12**) and chromadb's false telemetry error (**#13**, a `posthog` 6+ signature mismatch, not the environment setting).

**Sprint 3 (session persistence):**

- **Design first** (`docs/Persistence-Design.md`): what a conversation is made of (history, current node, the node's typed input, retry counters, conversation id), a SQLite store with one JSON row per session, opt-in on the pipeline so the eval harness and the existing tests are untouched, save after every completed turn, load by rebuilding rather than replaying, and four decisions the maintainer answered before any code (SQLite; explicit `--session`/`--resume` only; a finished conversation shows its transcript and says it ended; sessions kept until deleted by hand).
- **Built:** `SessionStore`, save and resume in `CustomerSupportPipeline`, CLI `--session`/`--resume`, Streamlit resume through `?session=<id>`, the `SESSION_DB_PATH` setting, a gitignored `data/` folder. 60 new tests (244 → 304), all without a model. The store and pipeline tests were mutation-checked: removing the counter, id, history or input restore, the save, or the resumable-input check each fails a test.
- **Verified live** against `llama3.2:3b`: CLI started, user identified, question asked, process killed, `--resume` replayed the transcript, did not ask to identify again and answered a follow-up from the premium KB; the Streamlit app opened in a fresh process on the same URL redrew the 5 saved messages with no second greeting and highlighted `AuthenticatedUserNode`. A full 122-entry golden-set run on the branch matches the previous run on every metric.
- **Found (#37), fixed afterwards (below):** after identification fails the bot said it could not verify the user but kept answering from the free KB. The persistence design refuses to resume such a session.

**Since the Sprint 3 merge (outside any sprint; logged in `docs/Sprints.md`):**

- **Documentation:** a process evaluation and improvement plan (`docs/Process-Evaluation.md`, #39), a rule that this report is updated in the same PR as any change that alters it (#40), and the report rewrite (#41).
- **#37 fixed (#42):** once identification fails, the fail-safe message ends the conversation (the maintainer chose this over returning to the greeting or answering free-tier questions on purpose). `AuthenticatedUserNode` is final when it holds no `UserProfile`. Golden-set entry `ident-014` sends a support question after the failure and passes only if nothing follows the fail-safe message and no retrieval runs; it failed on the old code (the payments question was answered from the free KB) and passes now. The fails-safe metric grows from 5 to 6 entries.
- **#33 fixed (#45):** each decline is taken out of the message before a request is looked for, so a message that declines one call and requests another counts. A 12-entry held-out cohort (`call-059`..`070`) was committed before any change: recall on it went from 2/7 to 7/7. One trade-off: `call-070`, a decline followed by a conditional offer ("call me back only if the email bounces"), now false-triggers, which moved full-set precision from 95.1% to 93.6%. It was not tuned away, since that would spend the held-out entry (`docs/eval/Callback-Compound-Results-2026-09-21.md`).
- **The with-audio path exercised (#10, #46), then fixed (#43, #44):** Whisper was fine, but the ticket step crashed the turn and installing the extra in a fresh venv failed. Both are fixed; see §10.6.
- **The license decided (#49, #14 partly):** the code and docs are MIT-licensed; `assets/NOTICE.md` records the KB text and call audio as third-party sample data of unconfirmed origin, which the license does not cover.
- **Run-to-run variance measured (#50):** five full 135-entry runs on unchanged code, 0 pp spread on every metric, 0 of 135 entries changing result; see §10.7.

**Sprint 4 (real user store, Phase 7):**

- **Design first** (`docs/User-Store-Design.md`): two decisions the maintainer answered before any code - SQLite as the real backend, and no second identification factor for this sprint.
- **Built:** `tools/user_store.py` - a `UserStore` protocol, `MockUserStore` (in-memory, unchanged fixture, kept for tests) and `SqliteUserStore` (real, auto-seeded on first open of an empty file, matching `SessionStore`'s self-healing-on-open posture). Both read one canonical copy of the fixture data through a shared matching helper, so mock and real cannot silently drift apart. `Settings.user_store_provider` (`mock`/`sqlite`, default `sqlite`) mirrors the existing `llm_provider` pattern; `tools/user_info_db.py` and its test file, now dead code, were removed.
- **34 contract tests**, parametrized over both stores, so a behavior difference between them fails a test instead of shipping.
- **Regression verified**, then an **end-to-end audit before merge** found and fixed five things none LLM-facing: a real seed race (`SELECT COUNT(*) == 0` then `INSERT`, confirmed with a forced-interleaving reproduction, fixed with `INSERT OR IGNORE`), a shared-mutable-fixture reference in `MockUserStore`, two style inconsistencies, broken test hermeticity (the store was resolved eagerly in `__init__`, so tests that faked out the graph entirely still wrote a real sqlite file), and SQLite connections never explicitly closed. See §10.8, §13 finding 33.

**Sprint 5 (CI regression gate, Phase 8):**

- **Design first** (`docs/Eval-Gate-Design.md`): a GitHub-hosted runner installing and caching Ollama, gating on a curated 14-entry subset - not a self-hosted runner (which GitHub warns against for public repos) and not a live-model-free gate (which wouldn't satisfy the sprint's own Definition of Done).
- **Built:** `scripts/eval_gate.py` (10 unit tests on the comparison logic, no live model needed) and a new `eval-gate` CI job, separate from `test` so the fast unit/lint signal never waits on a live model.
- **Proven for real, not simulated:** a disposable branch deliberately broke `_get_retriever` to always return the paid KB; `eval-gate` failed on it exactly as designed.
- **The proof caught a real incident:** that same disposable "TEST - DO NOT MERGE" PR was merged into `main` anyway, because `eval-gate` wasn't yet a *required* status check - a few minutes of `main` served every user the paid KB regardless of tier. Caught by checking the merge history directly, fixed with one `git revert -m 1` (hotfix PR #55), and `eval-gate`/`test` were both made required status checks the same day. See §10.9, §13 finding 34.

**Token-usage logging and the OpenAI comparison (outside any sprint, same day as Sprint 6):**

- **No token accounting existed before this.** A `TokenUsageCallbackHandler` (`logging_config.py`) attaches to the chat model at construction time in `config.get_chat_model()`, reading each provider's own `AIMessage.usage_metadata` and logging one `llm_usage` event per LLM call - fires for every call a model makes, including ones nested inside an `AgentExecutor` or a retrieval chain, without touching any individual call site.
- **Used to run a real, measured comparison** of `llama3.2:3b` vs `gpt-4o-mini` across the full 135-entry golden set, one run each, same code/KB/embeddings (embeddings stayed on local Ollama for both). See §10.10.

**Sprint 6 (UX/design polish, Phase 9):**

- **One technical question resolved before writing code:** the installed Streamlit (1.39.0, checked directly against its own `config.py`) supports exactly one static custom `[theme]` palette, with no runtime API to detect a viewer's light/dark selection - the light-column palette was set as the one custom theme rather than fighting the framework with fragile internal-CSS overrides.
- **Built:** `.streamlit/config.toml` (the palette); `app.py` - page title moved from brand copy to "Support", a subscription-tier badge via a new `CustomerSupportPipeline.current_user_profile` property, retry prompts as `st.warning` and ticket-confirmation messages as `st.success`, classified using the graph layer's own `GreetingNode.RETRY_PROMPT` copy and node identity rather than new UI-side heuristics. The Graph tab is untouched, as `Design.md` specifies.
- **Found and fixed along the way:** `.streamlit/` was already blanket-ignored in `.gitignore` (for secrets.toml-style local config), which would have silently swallowed the new theme file too - `.gitignore` now excludes only `config.toml` from that rule.
- **Regression verified:** a full 135-entry run, 0 of 135 entries changed result, all 8 metrics identical to the same-day baseline.
- **Closed afterwards (2026-09-23):** resumed sessions keep ticket-confirmation styling, and the theme was checked rendered in a real browser engine in both modes. See §10.11.

## 9. Methodology — Build History

136 commits and 38 merged pull requests as of #58. By pull request:

| PR | Branch | What it did |
|---|---|---|
| — | `main` (initial commit) | Sprint 0 MVP baseline (graph framework, identification, tiered RAG, call-me flow, Streamlit/CLI, 17 unit tests) plus two out-of-band fixes: stale editable install, Chroma duplicate-embedding bug |
| #1, #2, #3 | `sprint-1` | Sprint 1: eval metrics and targets, golden set (12 → 38), structured logging, automated harness, both identification auth-bypass fixes, harness fixes, whisper and callback-recall fixes, first hallucination grade |
| #4 | `chore/git-workflow` | Git workflow tooling: CI, pre-commit hook, PR template, line endings |
| #15 | `sprint-2` | KB rewrite, stricter answer prompt, reindex tooling (hallucination 20% → 6.7% on the tuned set) |
| #18 | `sprint-2-rag-golden-set` | 21 held-out `rag-*` entries; untuned hallucination 9.5% |
| #19 | `sprint-2-fix-16-17` | Fix #16 (manual-payments contradiction), block invented UI steps (#17, partial) |
| #20 | `sprint-2-lint-gate` | Fix all 27 ruff findings; lint is a hard CI gate (#9) |
| #21 | `sprint-2-callback-heldout` | Held-out callback set and stronger scoring (#8); precision 85% |
| #24 | `sprint-2-fix-22-extraction-leak` | Fix the wrong-number callback (#22) |
| #25 | `sprint-2-sprints-md-22` | Record the #22 fix in `Sprints.md` |
| #26 | `sprint-2-decide-7` | Record the #7 decision (keep the digit pre-check) |
| #27 | `sprint-2-callback-precision` | Callback precision 67% → 83% on the held-out cohort (#23, not met) |
| #28 | `sprint-2-larger-model` | Larger-model experiment: plan, both full runs, results |
| #31 | `fix/subscription-lookup-guard` | Identity guard fix (#29), sprint log entry |
| #32 | `sprint-2-closeout` | Sprint 2 close-out and report refresh |
| #34 | `sprint-2-final-fixes` | End-to-end audit: doc fixes, #11 lookup, #30 bounds, callback veto, retrieval-log warning; tag `v0.1.0-sprint2` |
| #35 | `chore/known-limits-milestone` | Docs: the accepted limits live in a `Known limits` milestone, not Sprint 3 |
| #36 | `fix/cli-eof-and-telemetry` | CLI exits cleanly on end of input (#12); the false chromadb telemetry error is dropped (#13) |
| #38 | `sprint-3` | Sprint 3: session persistence (SQLite store, save and resume in the pipeline, CLI `--session`/`--resume`, Streamlit resume by URL) |
| #39 | `docs/process-evaluation` | Docs: the process evaluation (`docs/Process-Evaluation.md`) and the report brought up to the Sprint 3 merge |
| #40 | `docs/keep-report-current` | Docs: the report and PR template say the report is updated with every change, not only at sprint end |
| #41 | `docs/report-refresh` | Docs: the report rewritten in the full report format and re-verified on `main` |
| #42 | `fix/37-failed-identification-ends-session` | Fix #37: a failed identification ends the conversation; golden-set entry `ident-014` |
| #45 | `fix/33-compound-callback-phrasings` | Fix #33: a request beside a decline counts; 12 held-out entries (`call-059`..`070`), one new false trigger (`call-070`) |
| #46 | `docs/10-whisper-path-result` | Docs: the with-audio path exercised (#10); it fails, filed as #43 and #44 |
| #47 | `docs/progress-update-2026-09-21` | Docs: bring every document up to date with #37, #33 and the with-audio path |
| #48 | `fix/43-44-audio-path` | Fix the with-audio path: structured ticket with a fallback (#43), a whisper pin that builds in a fresh venv (#44) |
| #49 | `chore/14-license` | License the code MIT; record the KB text and call audio as third-party sample data of unconfirmed origin (#14, partly) |
| #50 | `chore/eval-variance` | Measure run-to-run variance: five full 135-entry runs, 0 pp spread, 0 entries changed (§10.7) |
| #51 | `sprint-4` | Sprint 4: real user store (`SqliteUserStore`, Phase 7), 34 contract tests, an end-to-end audit before merge |
| #52 | `sprint-5` | Sprint 5: automated eval regression gate (`scripts/eval_gate.py`, a new `eval-gate` CI job, Phase 8) |
| #53 | `scratch/prove-eval-gate-catches-regression` | "TEST - DO NOT MERGE": a disposable tier-scoping break proving the gate catches a real regression - merged to `main` by mistake alongside #52 (the incident, §13 finding 34) |
| #54 | `hotfix/revert-tier-scoping-break` | Revert the bad merge commit (`git revert -m 1`) |
| #55 | `hotfix/revert-tier-scoping-break` | Hotfix: the revert, CI-verified green, merged |
| #56 | `docs/sprint-5-closeout` | Docs: close out Sprint 5 (Phase 8), record the merge incident honestly |
| #57 | `docs/record-required-checks-live` | Docs: record that `eval-gate` and `test` are now required status checks |
| #58 | `sprint-6` | Sprint 6: `.streamlit/config.toml` and `app.py` themed per `Design.md` (Phase 9), a `TokenUsageCallbackHandler` and the OpenAI-vs-local-model comparison, `docs/eval/` stopped being tracked |
| #59 | `fix/sprint-6-loose-ends` | Sprint 6 closeout: replies record the node their turn ended at, so resumed sessions keep ticket styling; theme checked in headless Edge in both modes, all text at WCAG AA |
| #60 | `chore/synthetic-kb` | Replace the Shopify-derived KB and the call of unknown origin with an original KB for the fictional Brightstall and a synthesized call; everything MIT (closes #14) |
| #61 | `fix/quality-targets` | Quality round 1: held-out cohorts committed first; a callback filter for number questions (#23) and guards against invented places and steps (#17, #5); closes #17 |
| #62 | `fix/session-recency-tie` | Make each save's time strictly later than the previous one; the Windows clock tie made `latest_unfinished()` return the wrong session and a test flaky |
| #63 | `fix/quality-round-2` | Quality round 2 for #5 and #23: a voice-request rule for statements, answers that turn a restriction around replaced by the restriction; all three held-out targets missed (§10.14). Open at the time of writing |

The working pattern since Sprint 2: criteria and held-out entries are committed **before** the run, fixes are developed only against entries already in the set, and the untouched cohort is run once afterwards (`docs/Git-Workflow.md`, the `docs/eval/` reports).

## 10. Results

### 10.1 Unit tests and lint

513/513 passing across 20 files — deterministic graph/domain/config/agent/reindex/lookup/timeout/CLI/persistence logic and the Streamlit app driven headlessly, no live model required (30 at the end of Sprint 1; 209 at the Sprint 2 close-out; 237 after the audit fixes; 244 after the CLI and telemetry fixes; 304 after Sprint 3; 312 after #37; 333 after #33; 335 after #43; 354 after Sprint 4; 364 after Sprint 5's hotfix; 371 after Sprint 6; 374 after its closeout; 375 after the save-time fix, #62; 446 after the quality fixes and held-out cohorts; 513 after quality round 2). `ruff check` reports no findings, including the whole repo since the notebook exclusion, and is blocking in CI (`src`, `tests`, `scripts`).

### 10.2 Live end-to-end re-verification (this update, merged `main` at #45, `a60d9f8`, `llama3.2:3b`)

Driven directly through the real pipeline against the local Ollama server; single conversations, so the timings are single observations, not a latency measurement.

| Conversation | What was sent | What came back | Checked |
|---|---|---|---|
| A: premium user | `michaeljackson@gmail.com` | "Hi, Michael Jackson … you have the premium subscription" at `AuthenticatedUserNode` (4.2 s) | identified |
| A | "Can I sell my products in person with a POS?" | "Yes, you can use Shopify POS to sell your products in person." (2.6 s); sources `assets/paid/{compliance,locations,pos}.txt` | paid KB only |
| A | "Please call me on 0452 333 666" | `CallCustomerNode`, conversation over: "We've logged your callback request for 0452 333 666 …" (0.3 s; the no-`audio`-extra variant) | callback with the typed number |
| B: free user | `0452 333 667` (a phone number, with spacing) | "Hi, John Doe … you have the free subscription" (3.9 s) | phone lookup works |
| B | the same POS question | "No, with a free subscription, you can only sell online. To sell in person with Shopify POS, you need a paid subscription." (2.9 s); sources `assets/free/{compliance,pos}.txt` | free KB only, different answer by tier |
| C: unknown user | three unidentifiable messages | two retry prompts, then "Sorry, we still couldn't verify your account …" | never authenticated, and the conversation is over (`ended` is true); before #37 it carried on and answered free-tier questions |
| D: session store | identify as `carl@sagan.com` with a store, then a new pipeline on the same session id | resumed at `AuthenticatedUserNode` with the 3-line transcript | resume works |

Also checked this update: `scripts/reindex_kb.py --check` (free 14 of 14 chunks, paid 15 of 15, none stale), `ruff` (clean), `pytest` (333 passed). The Streamlit app was not launched in a browser.

### 10.3 Eval harness — current state (`docs/eval/Post-Sprint3-FullEval-2026-09-21.md`, 135 conversations, 11 categories, `llama3.2:3b`, merged `main` at #45; every metric matches the Sprint 3 run except callback precision on the full set)

| Metric | Now | Target | End of Sprint 1 (38 entries) |
|---|---|---|---|
| Identification success rate | **100%** (n=8: `ident-007` and `ident-010` became scored after #11) | ≥95% clean / ≥80% ambiguous | 100% |
| Fails-safe rate | **100%** (n=6; `ident-014` added for #37) | 100% | 100% |
| Retrieval recall@k | **100%** (n=39) | ≥90% | 100% (n=12) |
| Tier-leakage rate | **0%** (n=39) | 0% | 0% (n=12) |
| Callback recall | **100%** (44/44, including the 7 compound requests added for #33) | ≥90% | 100% (n=7) |
| Callback precision, full set | **93.6%** (44/47: `call-042`, `call-047` and, since #33, `call-070`; it was 94.9%, 37/39, before the #33 cohort was added) | ≥95% | 100% (n=7) |
| Callback precision, held-out cohort (`call-037`..`058`) | **83%** (10/12) — **misses target** | ≥95% | not measured |
| Phone extraction | **100%** (44/44) | none | not measured (94% before the #22 fix, on a later 100-entry run) |
| Callback, #33 cohort (`call-059`..`070`, written before the fix) | recall **7/7**, precision **7/8** (`call-070` false-triggers) | ≥90% / ≥95% | not measured (recall 2/7 before #33) |
| Hallucination rate | see §10.4 — **misses target** | ≤5% | 20% (3/15) |

The callback rows are lower than Sprint 1's, and that is a *better* measurement, not a regression: Sprint 1's three negatives contained no digits, so the digit pre-check rejected them before the model was consulted and they could never fail. Precision only became informative once negatives that contain a number were added. The full-set 94.9% is inflated by entries the callback change was developed on; the held-out 83% is the honest figure. A fresh 3B full run on 2026-09-19 (`Model-Full-llama3-2-3b-2026-09-19.md`) and the audit's two runs scored callback recall 100% against 97% in the earlier full run on the same code, an unexplained small difference. The held-out 83% reproduced exactly, with the same two false triggers (`call-042`, `call-047`). Entry results: 120 pass, 3 fail (`call-042`, `call-047`, `call-070`), 12 manual review (the hand-graded hallucination set); on the 122 entries of the Sprint 3 run it was 108 pass, 2 fail, 12 manual. `ident-011` completed in this run; its hang was intermittent, so that is not proof it is gone. The full-set precision fell from 94.9% to 93.6% because of `call-070` alone; the original held-out cohort is unchanged at 83% (10/12) and the 36 older `call-*` entries have no false trigger.

### 10.4 Hallucination trajectory (hand-graded against the KB text, one reader)

| Grade | Set | Result |
|---|---|---|
| Sprint 1 | 15 `rag-*`, tuned | 20% (3/15) |
| After KB rewrite and prompt | same 15, tuned | 6.7% (1/15) |
| Untuned held-out | 21 new questions | 9.5% (2/21); 14% counting a KB-caused wrong answer |
| After #16/#17 fixes | 15-entry untuned cohort | fabrication 26.7% → 13.3% (2/15) |
| Blind grade, both models | 51 answered `rag-*` (3B) | 1 clear hallucination (2%); 7 (14%) counting borderline answers |

Target ≤5% is not clearly met on any untuned measure. The last row disagrees with the earlier ones (2% vs about 10%): it includes entries the fixes were tuned on, and the grade is one reader's judgment, so the model *comparison* in §10.5 is the safer reading than that absolute rate. None of these figures was re-graded for this update.

### 10.5 Larger local model (`docs/eval/Model-Experiment-Results-2026-09-20.md`)

`llama3.1:8b` vs `llama3.2:3b`, model only, same code, KB and golden set, criteria and decision rule committed first. **Not sufficient — it fails all three conditions.**

| Condition | Required | 3B | 8B |
|---|---|---|---|
| Held-out callback precision / recall | ≥95% / ≥90% | 83% / 100% | 100% / 80% |
| Clearly hallucinated answers (of 51) | ≥3 fewer | 1 | 1 |
| No regression | all hold | holds | identification 50%, fails-safe 60%, retrieval recall 62%, tier leakage 38% |

The 8B answers "no" to every message in the model-only intent check, so its 100% precision is not judgment; and it writes its second tool call as plain text instead of calling it, so the subscription is never looked up. That exposed the identity guard gap fixed as #29. It is also about 1.3x slower per entry and 4.9 GB against 2.0 GB.

### 10.6 The with-audio call path (exercised for the first time, 2026-09-21; fixed the same day, #43, #44)

First run: a separate venv on a short path (`C:envs\cs-audio`, Python 3.10.10, `openai-whisper` 20231106, `librosa` 0.10.2, `numexpr` 2.8.7, torch 2.14.0) so the project `.venv` was not touched. One conversation through the real pipeline, then a direct probe of the tool, `llama3.2:3b`, single observations.

| Step | First run | After the fix (`fix/43-44-audio-path`) |
|---|---|---|
| `pip install -e ".[audio]"` in a fresh venv | **Failed** on `ModuleNotFoundError: No module named 'pkg_resources'` in a source build (#44). Worked only with `setuptools<70` and `--no-build-isolation`. | Works with no workaround, in a new short-path venv (`C:envs\cs-audio-44`, `pip install -e ".[audio,dev]"`, exit 0, no `pkg_resources` in the log) |
| Whisper `base` transcribing `assets/audio/customer_support.wav` (55.5 s) | Works: 19.2 s on CPU, transcript accurate (agent Ruby, customer Michael, a point-of-sale subscription problem, a ticket opened) | Unchanged |
| Ticket step, `call_customer` run twice directly | Returned the identical `PhoneCallTicket` JSON *schema* both times (temperature 0), so it was deterministic (#43) | Returns a filled-in ticket, identical on two runs: `{"agent_name":"Ruby","customer_name":"Michael","call_summary":"A customer, Michael, contacts Shopify's Ruby for help with issues with his point of sale system. Ruby confirms Michael's email and date of birth, and informs him that there is no problem with his subscription. Ruby offers to open a ticket for support, which should be resolved within 2 hours."}` |
| Callback turn through the pipeline | **Crashed** with an uncaught `OutputParserException` | Completes: the reply names Ruby, says a ticket was created, and shows the summary above (11.8 s on a second run, 33.6 s on the first with the model still loading) |

**Root cause of #43.** The ticket was asked for as free text with the schema spelled out in the prompt, and the 3B model echoed the schema back. The fix asks for it with structured output (`with_structured_output(PhoneCallTicket)`), the mechanism the identification chain already uses, and `CallCustomerNode.greeting_message()` catches a ticket it cannot read and gives the "callback logged" reply, so a bad ticket can no longer end a conversation. That fallback has a model-free unit test, which fails on the old code. The first structured version truncated `call_summary` to its first clause ("A customer, Michael, contacts Shopify"), identical on two runs; telling the prompt to keep the whole summary fixed it. The summary chain itself was never at fault.

**Root cause of #44.** `openai-whisper` releases up to `20240930` build from source with a `setup.py` that imports `pkg_resources`, which pip's isolated build gets from the newest `setuptools`, and that no longer ships it. Reproduced on `20231106`, `20231117` and `20240930`; `20250625` builds. The extra now pins `20250625`. The unit suite (335 tests) passes in the new venv and in the project `.venv`, and the two agree on `numpy` 1.26.4, `langchain` 0.3.7 and `langchain-core` 0.3.63.

Limits: single observations on one machine, one recording, one local model. Not tried: `llama3.1:8b`, or Linux/macOS (the pin builds on Windows only as far as tested). The golden set does not exercise this path, so it was not re-run. The tool always transcribes the same fixed recording, so every ticket describes that call whoever asked. Without the extra the callback path still works as in §10.2.

### 10.7 Run-to-run variance (measured 2026-09-21 to 22)

Five full 135-entry runs of unchanged `main` (`8d450ae`), `llama3.2:3b`, criteria fixed beforehand in `docs/eval/Variance-Plan-2026-09-21.md`, results in `docs/eval/Variance-Results-2026-09-22.md`, raw reports in `docs/eval/variance/`.

| Question | Result |
|---|---|
| Do aggregate metrics move? | No: identical in all five runs (spread 0.0 pp on all eight); 120 PASS, 3 FAIL, 12 MANUAL REVIEW every time |
| Does any entry change result? | No: 0 of 135 |
| Does any output change? | One: `rag-free-008` answered at 186 characters in run 1 and 327 in runs 2-5. Retrieval was identical and the RAG prompt carries no history, so the difference is generation on the model server, not this project's code. The 12 hand-graded entries' answers were byte-identical in all five runs |
| The earlier 100% vs 97% recall difference? | One entry, `call-031`, which is decided by the model's intent check and failed once in eleven full 3B runs on record. Not reproduced in five runs, not ruled out (a 10% per-run flip rate would still give five clean runs about 59% of the time), and its cause is unknown |

Limits: five runs, one machine, one night. "0 flippers" is a lower bound on the true range; a 2026-09-23 replay did see answer text change for 9 of 73 dev questions (§13 finding 39). Wall time was steady at 783-796 s per run. Not tested: attributing a flip (the plan's Phase 2 was skipped because none occurred), warm versus cold model state beyond run 1, or another day. Compare runs with `scripts/summarize_eval_runs.py`.

### 10.8 Sprint 4 regression check (real user store, `docs/eval/Sprint4-UserStore-FullEval-2026-09-22.md`, branch `sprint-4`)

Sprint 4 (Phase 7) changed only where identification data comes from - `SqliteUserStore` in place of the old in-memory lists, auto-seeded with the same four users - and touched no LLM-facing code, so the regression bar is exact equality with the last full run on unchanged `main`, not just "within target."

A fast 14-entry `ident-*`-only run (`--ids`, seconds not minutes) was run first as a sanity check before committing to the full 135-entry run: identification success 100% (n=8) and fails-safe 100% (n=6), matching the baseline exactly. The full run then confirmed it with no gaps, diffed against `docs/eval/variance/run-5.md` (the latest full run on unchanged `main`) with `scripts/summarize_eval_runs.py`:

| Metric | `main` (run-5) | `sprint-4` | Spread |
|---|---|---|---|
| Identification success | 8/8 (100%) | 8/8 (100%) | 0.0 pp |
| Fails-safe | 6/6 (100%) | 6/6 (100%) | 0.0 pp |
| Retrieval recall@k | 39/39 (100%) | 39/39 (100%) | 0.0 pp |
| Tier leakage | 0/39 (0%) | 0/39 (0%) | 0.0 pp |
| Callback recall | 44/44 (100%) | 44/44 (100%) | 0.0 pp |
| Callback precision | 44/47 (93.6%) | 44/47 (93.6%) | 0.0 pp |
| Phone extraction | 44/44 (100%) | 44/44 (100%) | 0.0 pp |
| Callback false-trigger rate | 3/38 (7.9%) | 3/38 (7.9%) | 0.0 pp |

0 of 135 entries changed result (120 pass, 3 fail, 12 manual review, identical to run-5). The only text-variant entry is `rag-free-008`, the same generation-wording variance already characterized as normal in §10.7 - not a new effect of this sprint.

Also checked live (§10.2-style): identify by email (`michaeljackson@gmail.com`) and by phone (`0452 333 667`) through the CLI against the real `data/users.sqlite`, both resolving the correct name and tier and answering the same POS question from the correct KB, matching the mock-backed behavior exactly.

**End-to-end audit, before merge** (`docs/Sprints.md`, mirroring Sprint 2's own audit-before-tag practice). A manual pass plus a backgrounded automated code review over the full `main..sprint-4` diff found and fixed five things, none LLM-facing (re-verified with the full unit suite and a live CLI check, not a second golden-set run):

- A real race in the auto-seed (`SELECT COUNT(*) == 0` then `INSERT`) that could crash a second concurrently-opening store on the `user_id` primary key - confirmed with a forced-interleaving reproduction, fixed with `INSERT OR IGNORE`, guarded by a new concurrency test.
- `MockUserStore` held references to the shared fixture lists rather than copies - latent, since nothing writes through a store yet, but fixed with a defensive copy.
- Two style inconsistencies with the rest of the codebase (lowercase generic type hints, an `__init__` using `*args`/`**kwargs`) made explicit to match `session_store.py`'s conventions.
- Broken test hermeticity: the user store was resolved eagerly in `__init__`, so tests that fake out `_get_pipeline()` entirely were still writing a real `data/users.sqlite` on every run, silently contradicting a test named `test_without_a_store_nothing_is_saved_and_there_is_no_session`. Fixed by resolving it inside `_get_pipeline()`, matching what `docs/User-Store-Design.md` specified from the start (the implementation had drifted from its own spec).
- SQLite connections were never explicitly closed (`with conn:` only manages the transaction), unlike `SessionStore`'s `closing(...)` pattern. Fixed to match.

354/354 tests pass, ruff clean, after the fixes.

### 10.9 Sprint 5: CI regression gate (`docs/Eval-Gate-Design.md`)

`scripts/eval_gate.py` runs 14 hand-picked golden-set entries (one or two per category,
weighted toward tier-leakage and callback) against the real pipeline and fails if any
entry that wasn't failing starts failing, compared to a checked-in baseline
(`tests/eval/ci_baseline.json`). Aggregate metrics are computed and printed for context
only, not a second gate - on a fixed 14-entry set they're fully determined by the same
per-entry results already checked, so a metric-floor check would just restate a
regression already caught, not add detection power. Wired into CI as a new `eval-gate`
job, separate from the existing `test` job so the fast unit-test/lint signal never waits
on a live model; PR-only (`main` is already gated at PR time).

**Verified against real GitHub Actions, not simulated.** First run (cold cache): Ollama
install, both model blobs pulled, 14-entry inference, 13m13s total, passed. A disposable
branch then deliberately broke `_get_retriever` to always return the paid KB regardless
of tier; the `eval-gate` job **failed** on it (`rag-adv-001`/`rag-adv-002`, tier leak),
exactly as designed - this is Sprint 5's own literal Definition of Done, proven, not
asserted.

**The proof also caught a real incident.** `eval-gate` reporting red does not yet block a
merge: it isn't marked as a *required* status check in GitHub's branch protection
settings (`docs/Git-Workflow.md` already flagged this as a manual step still needed). The
disposable "TEST - DO NOT MERGE" proof PR - labelled that in its title, body, and the
code comment itself - was merged into `main` anyway, alongside the real Sprint 5 PR. For a
few minutes, every user of the deployed code path would have been served the paid
knowledge base regardless of their actual subscription tier. This was caught by checking
`main`'s actual merge history directly rather than trusting a status summary, fixed with
`git revert -m 1` of the one bad merge commit (hotfix PR #55, itself confirmed green on
CI - both `eval-gate` and `test` passing on the revert - before being merged), and
verified live afterward. 363/364 tests passed on the hotfix branch; the one failure,
`test_latest_unfinished_returns_the_most_recently_saved_open_session`
(`tests/test_session_store.py`), is a pre-existing timestamp-ordering timing flake
unrelated to this change (passes in isolation, fails intermittently as part of the full
suite; not introduced by Sprint 4 or 5, both of which leave that file untouched) - open as
its own small follow-up, not part of this incident.

**Net effect:** the gate mechanism itself is proven correct, and the process gap that let a
correctly-failing check still get merged is now actually closed (both `test` and
`eval-gate` are required status checks under branch protection as of 2026-09-22), not just
documented as an open item - wiring the CI job in was necessary but, this incident showed,
not by itself sufficient.

### 10.10 OpenAI vs local model, first exercise (`docs/eval/Compare-Ollama-vs-OpenAI-2026-09-22.md`)

`llama3.2:3b` vs `gpt-4o-mini`, chat model only (embeddings stayed on local Ollama for
both), same code, KB and 135-entry golden set, one full run each. No token accounting
existed before this - a `TokenUsageCallbackHandler` (`logging_config.py`) was added,
attached to the chat model in `config.get_chat_model()`, reading each provider's own
`usage_metadata` so both providers' figures below are measured, not estimated.

| Metric | Target | Ollama (3B) | OpenAI (`gpt-4o-mini`) |
|---|---|---|---|
| Identification / fails-safe / retrieval recall / tier leakage / callback recall | various | 100% / 100% / 100% / 0% / 100% | same, all 100% / 0% |
| **Callback precision** | ≥95% | **94% (n=47)** | **98% (n=45)** |
| Callback false-trigger rate | none | 8% (n=38) | 3% (n=38) |
| LLM calls | — | 692 | 275 (-60%) |
| Total tokens | — | 359,094 | 155,973 (-57%) |
| Wall-clock | — | 13.4 min | 16.9 min (network latency per call outweighs having 2.5x fewer calls) |
| Cost, this run | — | $0 (local) | $0.0265 |

**OpenAI closed the one metric Sprint 2 carried forward as an accepted known limit
(#23).** The two entries that flip PASS, `call-042` and `call-047`, are the exact same
two false triggers `Model-Experiment-Results-2026-09-20.md` (§10.5) names as the 3B's
weak point - both contain a phone number and phone-adjacent wording ("format...for the
checkout form", "phone support") without an actual callback request, and the 3B's
LLM-based intent check (`PydanticTextBasedEdge.check()` in `CallCustomerEdge`, reached
only when the deterministic regexes don't match) says yes where `gpt-4o-mini` says no.
Everything else held identical, including all three `out_of_scope_question` refusals
verbatim. Cost note: the same tokens would have cost $0.085 on `gpt-3.5-turbo` (still
`.env.example`'s default model name) - over 3x more for a model that does not close the
precision gap.

Limits: one run per backend (as in §10.5 and §10.7), hallucination rate not re-graded,
wall-clock is one data point per backend on one machine, sequential not simultaneous.

### 10.11 Sprint 6: UX/design polish (`docs/Design.md`, Phase 9)

Applied `Design.md`'s theme/typography spec to `app.py` for the first time (it was a bare
default Streamlit app through Sprint 5). One technical question resolved before writing
any code: the installed Streamlit (1.39.0, checked directly against its own
`config.py`) supports exactly one static custom `[theme]` palette, with no runtime API in
this version to detect a viewer's light/dark selection and serve a second palette. Rather
than fight the framework with fragile internal-CSS overrides, the light-column palette
was set as the one custom theme; a viewer's manual dark-mode toggle gets Streamlit's own
built-in dark defaults, not `Design.md`'s dark column - documented as a deliberate limit,
not silently claimed as full parity.

**Shipped:** `.streamlit/config.toml` (the palette); `app.py` - page title changed from
brand copy to "Support" (§3), a subscription-tier badge (`st.caption`) once identified via
a new `CustomerSupportPipeline.current_user_profile` property, retry prompts as
`st.warning` and ticket-confirmation messages as `st.success` (§4), classified using the
graph layer's own `GreetingNode.RETRY_PROMPT` copy and node identity rather than new UI-side
heuristics (per `docs/Rules.md`). The Graph tab is untouched, as specified.

**Regression check** (this sprint's explicit Definition of Done, since it touches no
LLM-facing code the bar is exact equality, the same standard §10.8 held itself to):
`docs/eval/Sprint6-UX-FullEval-2026-09-22.md` against the same-day baseline
`docs/eval/Compare-Ollama-FullRun-2026-09-22.md` -

| Metric | Baseline | Sprint 6 | Spread |
|---|---|---|---|
| Identification success | 8/8 (100%) | 8/8 (100%) | 0.0 pp |
| Fails-safe | 6/6 (100%) | 6/6 (100%) | 0.0 pp |
| Retrieval recall@k | 39/39 (100%) | 39/39 (100%) | 0.0 pp |
| Tier leakage | 0/39 (0%) | 0/39 (0%) | 0.0 pp |
| Callback recall | 44/44 (100%) | 44/44 (100%) | 0.0 pp |
| Callback precision | 44/47 (94%) | 44/47 (94%) | 0.0 pp |
| Phone extraction | 44/44 (100%) | 44/44 (100%) | 0.0 pp |
| Callback false-trigger rate | 3/38 (8%) | 3/38 (8%) | 0.0 pp |

0 of 135 entries changed result.

**Tests:** `_FakePipeline` in `tests/test_app_sessions.py` gained a matching
`current_user_profile` attribute; 5 new AppTest tests (badge present/absent, a live
ticket message renders as `st.success`, a retry message as `st.warning` both live and on
resume) plus 2 new tests for the pipeline property itself. 371/371 pass (up from 364),
`ruff` clean.

**Limits, written down rather than hidden:** (1) dark mode is Streamlit's own palette, not
`Design.md`'s exact dark hex values - a `config.toml` capability limit in this Streamlit
version. (2) `st.success`/`st.warning` use Streamlit's built-in alert colors, not
`Design.md`'s exact success/warning hex codes - chosen over custom CSS per the design
doc's own stated preference.

**Closeout (2026-09-23).** The two items this section originally left open are closed.
(a) *Resumed ticket styling:* each saved assistant reply now records the node its turn
ended at, so `_message_kind()` classifies a resumed reply exactly as it does a live one.
No schema migration was needed, since messages are a JSON list; sessions saved before the
change replay their tickets as plain text. (b) *Browser check:* rendered in headless Edge
(Playwright, throwaway venv) against seeded sessions, in the custom light theme and in
Streamlit's built-in dark theme, with WCAG contrast computed from the rendered styles.
Everything passes AA: body text 17.4:1 / 18.1:1 (light / dark), ticket confirmation
5.51:1 / 11.8:1, retry warning 4.66:1 / 11.0:1, tier badge 4.57:1 / 6.9:1. The retry
warning and the badge pass by a hair in light mode. It also showed that an OS-level dark
preference is ignored once a custom theme is set; only Streamlit's settings-menu toggle
switches to dark, where accents are Streamlit red rather than `Design.md`'s green.

### 10.12 Synthetic knowledge base and call audio (#14, 2026-09-23)

The KB text read as Shopify help-center content and the call recording's origin was never
recorded, so neither could be licensed with the code. Both were replaced with original
material: a KB for **Brightstall**, a fictional platform, with the same files, tiers and
tested facts, and a scripted call synthesized with the Windows speech engine
(`scripts/generate_sample_call.ps1`). `assets/NOTICE.md` records the origin of every file;
the whole repository is now MIT.

| Metric | Old KB (`Sprint6-UX-FullEval`) | Brightstall KB (`SyntheticKB-FullEval`) |
|---|---|---|
| Identification success | 8/8 (100%) | 8/8 (100%) |
| Fails-safe | 6/6 (100%) | 6/6 (100%) |
| Retrieval recall@k | 39/39 (100%) | 39/39 (100%) |
| Tier leakage | 0/39 (0%) | 0/39 (0%) |
| Callback recall | 44/44 (100%) | 44/44 (100%) |
| Callback precision | 44/47 (94%) | 44/48 (92%) |
| Phone extraction | 44/44 (100%) | 44/44 (100%) |
| Hallucination (hand-graded, answered `rag-*`) | not re-graded | 4/51 (7.8%) |

One entry changed result: `call-024`, now a false trigger. The callback check reads the
conversation history but not the KB, and the history opens with the new greeting text, so
this is a wording effect on a borderline entry. The four hallucinations are all #17's
class (invented places or steps for "how do I" questions). Retrieval recall@4 on a 13-chunk
index covers about 31% of the corpus, so its 100% still says little (§15). The sample call
was run through the real tool once: an accurate transcript and a ticket naming Ruby and
Michael. The old files remain in git history.

### 10.13 Quality targets on the Brightstall KB (#5, #17, #23, 2026-09-23)

Held-out cohorts and criteria committed before any fix (22 RAG, 30 callback entries), fixes
designed on the existing entries, cohorts run once (`docs/eval/QualityFixes-FullEval-2026-09-23.md`).
Two deterministic changes: a callback filter for questions that hold a number but never
mention voice contact (#23), and a guard against answers that name a place or steps the
context does not give for the task (#17, #5). A second-pass grounding check by the 3B model
was tried first and rejected: it caught none of the four dev hallucinations.

| Criterion | Held-out result | Met |
|---|---|---|
| #17: invented steps or menu paths | 0/22 | Yes |
| #23: callback precision >= 95% | 12/12 (100%) | Yes |
| #23: callback recall >= 90% | 12/15 (80%) | No |
| #5: hallucination <= 5% | 1/22 (4.5%) lenient, 2/22 (9.1%) strict | Lenient only |
| Machine-scored metrics | no regression (retrieval recall 100% and leakage 0% at n=55) | Yes |

On dev the four hallucinations became refusals and only the two intended callback entries
changed result. The recall misses are statements the model declines, which the filter never
touches; the remaining cohort hallucination is a tier trap (`rag-adv-013`) the guards do not
target. The price is refusals of partly covered questions (two on dev, two on the cohort).
One run, one grader, small n: a 1-in-22 difference decides the #5 verdict.

### 10.14 Quality round 2 (#5, #23, 2026-09-23)

A second round with 50 new held-out entries and criteria committed first, the fixes designed
on everything already seen, and the full 237-entry set run twice (the two runs agreed on
every cohort entry).

| Criterion | Round-2 held-out | Met |
|---|---|---|
| #23 recall >= 90% | 10/13 (77%) | No |
| #23 precision >= 95% | 10/11 (91%) | No |
| #5 hallucination <= 5% (strict) | 2/20 (10%) | No |
| No regression | none | Yes |

The fixes (a voice-request rule for statements; replacing an answer that turns a stated
restriction around) closed the round-1 failures they were designed on: round-1 callback
recall rose from 80% to 93%. Every round-2 miss came from the model's own decision on a path
the rules do not cover, and the model refused 6 of 9 free-tier trap questions rather than
state the restriction. Two rounds of deterministic fixes have not converged on the targets
for `llama3.2:3b`; each unseen cohort finds new failure paths. The measured alternative is
a stronger model (`gpt-4o-mini` cleared callback precision on the full set, §10.10).

## 11. Evaluation Metrics

| Metric | Value |
|---|---|
| Unit tests passing | 513/513 (20 files) |
| Live end-to-end checks on merged `main` | 7/7 pass (identify by email and phone, paid-only and free-only retrieval, callback, fail-safe, resume) |
| CI | 71/73 runs green as of this update; the 2 non-green are the deliberate Sprint 5 proof failure and one superseded/cancelled duplicate run, not real breakage. `eval-gate` and `test` are both *required* status checks under branch protection since 2026-09-22 - see §10.9 |
| Golden-set size | 135 conversations across 11 categories (122 in the Sprint 3 run) |
| Golden-set run, post-Sprint 3 (#45) | 120 pass, 3 fail (`call-042`, `call-047`, `call-070`), 12 manual review (Sprint 3: 108 pass, 2 fail, 12 manual, on 122 entries) |
| Held-out sets written before their run | 21 `rag-*`, 16 + 22 callback, 15 for #16/#17, 10 for #22, 12 for #33 |
| Identity bypass/fabrication bugs found and fixed | 3 |
| Eval-harness bugs/gaps found and fixed | 3 in Sprint 1, plus a stronger callback scorer in Sprint 2 |
| KB content defects fixed | 2 (#6, #16) |
| Ruff findings | 27 → 0, enforced in CI |
| Retrieval recall / tier leakage | 100% / 0% (n=39) |
| Callback recall / precision (full set) | 100% / 93.6% (44/47); held-out cohort (`call-037`..`058`) precision 83% (95% interval 55% to 95%) |
| Hallucination | 13.3% fabrication on an untuned cohort; 2%-14% on the blind 51-answer grade; target ≤5% |
| Run-to-run variance (5 full runs, unchanged code) | 0 pp on every aggregate metric, 0 of 135 entries change result, 1 answer varies in wording (`rag-free-008`); §10.7 |
| Issues | #14 closed (§10.12); #17 closed (§10.13); #5 and #23 open after two rounds (§10.13, §10.14) |
| Commits / PRs | 136 commits, 38 merged PRs as of #58; single contributor |
| Token usage, full 135-entry golden set (measured, not estimated; §10.10) | `llama3.2:3b`: 692 LLM calls, 359,094 tokens, $0 (local). `gpt-4o-mini`: 275 calls, 155,973 tokens, $0.0265 |
| Since Sprint 3 | Sprint 4 (real user store, #51), Sprint 5 (CI regression gate, #52) and its hotfix (#55) for a merge incident found by Sprint 5's own proof (§10.9), token-usage logging and a measured OpenAI comparison (§10.10), and Sprint 6 (UI polish, #58, §10.11); plus #37, #33, #43, #44 fixed out of band |

## 12. Result Analysis

The core product meets its target on every machine-scored metric except callback precision on unseen messages, and misses the hallucination target. Sprint 2's central lesson is about measurement: the numbers that looked good were the ones measured on entries the fixes were built against (6.7% hallucination on the tuned 15, 100% callback precision on negatives with no digits), and each honest re-measure on held-out entries came out worse (9.5%, 83%). Committing the held-out entries before running them, and developing fixes only against entries already in the set, is what made the shortfalls visible instead of hidden.

The levers were spent in order of cost. Triage showed generation, not retrieval, was at fault; a stricter prompt and a KB rewrite helped; a deterministic guard removed one failure class; deterministic patterns bought callback precision but every wording change alone lost recall. The last cheap lever, a larger local model, was tested under criteria fixed in advance and did not help: it removed no hallucinations, lowered callback recall, and broke identification. Its failure was itself useful, exposing an identity-guard gap that would have let any model that skips a tool call silently assign a tier, now fixed. What remains is expensive or risky (more patterns that would overfit a 22-entry cohort, or a second-pass grounding check that adds a model call per answer), which is why the maintainer accepted carrying both accuracy targets as known limits rather than continuing to tune them (`docs/Sprints.md`).

Sprint 3 changed the product's shape, not its accuracy: persistence is opt-in on the pipeline, so the eval harness runs exactly as before and every metric held, and the live checks confirm a saved conversation resumes at the same node. The process evaluation adds a caution about the numbers themselves: at these sample sizes several targets cannot be confirmed either way (held-out callback precision of 10/12 has a 95% interval of 55% to 95%; hallucination of 2/15 has 4% to 38%), so the honest reading of "target not met" is "not shown to be met", and the next gain in trust comes from more and better-separated test data, not more tuning.

The work after Sprint 3 repeated the same lessons in miniature. #37 sat unmeasured because every identification entry checked the fail-safe message on the failing turn and none checked the turn after it; the fix added an entry that sends a question after the failure, and it was confirmed to fail on the old code before it was trusted. #33 shows the #23 trade-off again: taking declines out of the message recovered all five compound requests on a cohort committed first, and cost one conditional case (`call-070`) that was labelled before the change and was not tuned away, so full-set precision moved from 95.1% to 93.6% on one entry. And exercising the with-audio path found a deterministic crash that had been invisible for as long as the extra stayed optional: "a callback works" was true only without it.

Sprints 4 and 5 changed the product's shape again without changing its accuracy, the same pattern as Sprint 3: Sprint 4 swapped where identification data comes from behind an unchanged interface, and the full golden-set run showed exact equality with the prior baseline, not just "within target" - the right bar for a change with no LLM-facing surface. Sprint 5 didn't change the product at all; it made the existing evaluation self-enforcing, and its own proof of that (a deliberately broken retriever) is also the report's best evidence that the gate mechanism itself works, not simulated. The incident it also caught - a red check that didn't yet block a merge - is the sharper lesson: a gate that reports correctly is necessary but not sufficient without the branch-protection wiring to make it binding, and that gap is now closed, not just documented.

The OpenAI comparison is the first evidence in this project that the accuracy gap is a property of the small local model, not of the pipeline's design: `gpt-4o-mini`, on the identical code, KB and golden set, cleared the one target the 3B has carried as a known limit since Sprint 2 (callback precision), using fewer tokens, for about three cents. This doesn't retire the known limit - the shipped default is still `llama3.2:3b`, and the limit still applies to it - but it narrows what "known limit" means: not an inherent ceiling on this architecture, but a cost the maintainer accepted for staying local and free. Sprint 6 is the one change in this report with no accuracy claim to make either way, deliberately: it touches presentation only, and its own regression run (0 of 135 entries changed) is the proof that "UI polish" and "LLM-dependent behavior" really are separable concerns in this codebase, not just an assumption about the two other design docs.

The work of 2026-09-23 closed everything that was fixable by construction and measured, twice, what was not. Replacing the knowledge base (§10.12) was a content change with no intended accuracy effect, and the full run confirmed it: every machine-scored metric held except one borderline callback entry, moved by the new greeting text rather than by the KB. The two quality rounds (§10.13, §10.14) then followed the Sprint 2 method with its weakest point removed: the held-out cohorts were written and committed before any fix, with the pass criteria in the same commit. That discipline is what makes the result readable. #17 closed cleanly, because its failure class (invented places and steps) is visible in the text of an answer and a deterministic check can see it. #5 and #23 did not: each round's rules fixed the failures they were designed on (round-1 callback recall 80% → 93%; the dev tier-trap and yes-lead errors), and each fresh cohort found new failures on paths the 3B model decides for itself. Two cheaper alternatives failed outright and are worth recording: the 3B model as its own grounding checker caught none of the four dev hallucinations, and a prompt rule for plan restrictions made paid customers hear that their plan lacked what it has. Round 2 also showed that the model is not byte-stable between runs on this machine (9 of 73 dev answers differed), which is why its verification ran twice; the two runs agreed on every cohort entry, so the misses are not noise.

## 13. Auditing & Validation of Outcomes

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | Stale editable install — `customer_support_app` failed to import at all | High | Fixed |
| 2 | Chroma RAG index re-embedded and duplicated on every process start | High | Fixed |
| 3 | Callback-intent detection missed genuine requests. Originally recorded as "non-deterministic"; actually a deterministic bias from the internal `system:` message shown to the intent classifier | Medium | Fixed. Behavior change: a callback request must include a number (#7 decision) |
| 4 | `ANONYMIZED_TELEMETRY=False` doesn't silence chromadb's telemetry warnings | Low (cosmetic) | Fixed (#13). The setting worked; the errors came from chromadb calling `posthog.capture` in a way `posthog` 6+ rejects, so that one message is now dropped from that one logger |
| 5 | CLI has no graceful exit path (`EOFError` on stdin exhaustion) | Low | Fixed (#12): "Goodbye.", exit code 0 on end of input, `quit` or `exit` |
| 6 | Identification accepted garbage/unmatched input and fabricated a schema-valid `UserProfile` | Critical | Fixed |
| 7 | Sharper variant of #6: a fabricated tool-call argument matched a *real* account | Critical | Fixed |
| 8 | Call-me ticketing crashes (`ModuleNotFoundError: whisper`) without the optional `audio` extra | High | Fixed (degrades to "callback logged"). With the extra installed the path was exercised on 2026-09-21, crashed the turn, and was then fixed (finding 29, #43) |
| 9 | Hallucination on adversarial tier-crossing questions: retrieval stayed scoped but the answer contradicted its own context | Medium | Partly fixed, open (#5): see finding 19 and §10.4 |
| 10 | Eval harness: `KeyError` on two open-ended golden entries | Medium | Fixed |
| 11 | Eval harness: callback recall conflated "never fired" with "fired, then crashed" | Medium | Fixed |
| 12 | Mock DB lookup is case-sensitive and email-only, despite the greeting asking for a phone number | Low | Fixed (#11), in the final audit fixes |
| 13 | Hallucination rate 3/15 = 20% against ≤5% (Sprint 1 grade) | Medium | Superseded by §10.4; target not met |
| 14 | Free-tier KB contradicts itself on in-person selling | Low | Fixed (#6, KB rewrite) |
| 15 | Harness gap: out-of-scope entries had no `final_node` check, hiding a false callback trigger | Medium | Fixed |
| 16 | Sprint 1's callback precision of 100% was uninformative: the original negatives had no digits, so the pre-check rejected them before the model ran. Held-out negatives with numbers gave 85%, then 67% on the later cohort | Medium | Measurement fixed; the underlying false triggers are open (#23, now 83%) |
| 17 | Callback extraction returned the profile phone number instead of the one the user typed (`call-007`, 5/5 runs), because the extraction prompt included the internal profile line | High | Fixed (#22) |
| 18 | Free KB contradicts itself on manual payments (`payments.txt` lines 8 vs 46) | Medium | Fixed (#16) |
| 19 | Model invents UI steps for "how do I..." questions the KB doesn't answer | Medium | Partly fixed: guard removes click paths; 13.3% fabrication remains on an untuned cohort. Open (#17) |
| 20 | Identity guard rejected an *empty* subscription result but not a lookup that never ran, so the extractor invented the tier (assigned "free" to premium users). Latent with the shipped 3B; found via the 8B | Medium | Fixed (#29): lookup required, tier from the DB record, record must match the user |
| 21 | LLM calls have no generation cap or timeout; the 3B intermittently generates to the context limit, hanging `ident-011` (also on unmodified `main`) | Medium | Fixed (#30): bounded calls, timeout becomes a reply. Verified by unit tests; the hang is intermittent, so one clean live run is not proof |
| 22 | The larger local model (`llama3.1:8b`) writes tool calls as text and answers "no" to every callback intent check | Info | Documented; not adopted (§10.5) |
| 23 | README recommended `llama3.1:8b` for flaky flows, contradicting the experiment that rejected it | Low | Fixed |
| 24 | `RetrievalNode` swallowed any exception in the retrieval-log lookup that recall and tier-leakage scoring read | Low | Fixed: logs a warning |
| 25 | "No need to call me back, my number is ..." started a callback (the do-not-call veto did not know "no need") | Medium | Fixed. The compound case (declines and requests in one sentence) was fixed later (finding 31, #33) |
| 26 | Public repository with no LICENSE; the KB is Shopify-derived | Medium | Fixed (#14): code and docs MIT-licensed, and the third-party assets replaced by an original, synthetic knowledge base and a synthesized call, all MIT (§10.12) |
| 27 | After three unidentifiable messages the bot says it could not verify the user, then keeps answering from the free KB (confirmed live on 2026-09-20). Contradicts the PRD; impact limited to the free KB, tier leakage stays 0% | Low | Fixed (#37, PR #42): the fail-safe message now ends the conversation. Not caused by persistence. New golden-set entry `ident-014` fails on the old code and passes now; §10.2 conversation C |
| 28 | Process (`docs/Process-Evaluation.md`): targets cannot be confirmed at the sample sizes used, the golden set has been reused across about 15 runs, eval runs carry no manifest (git SHA, model digest, settings), the 20 PRs measured had 0 reviews, and docs plus eval reports are about 9 times the source | Medium | Open. A ten-point plan is proposed, not adopted; suggested first step is one PR for data splits, interval reporting and run manifests |
| 29 | With the `audio` extra installed, a callback request crashes the conversation: the 3B returns the ticket's JSON schema instead of a ticket (identical on two runs at temperature 0) and the exception is uncaught. Found by exercising the path for the first time (§10.6) | High for that configuration (an optional extra) | Fixed (#43): structured ticket, plus a fallback to the "callback logged" reply if a ticket cannot be read |
| 30 | Installing the `audio` extra into a fresh venv fails on `pkg_resources` in a source build; it worked with `setuptools<70` and `--no-build-isolation` | Low | Fixed (#44): the extra pins `openai-whisper==20250625`, which builds in a fresh venv |
| 31 | The do-not-call veto refused a message that declines one call and requests another ("Never call me before 9am, but do call me on X") | Medium | Fixed (#33, PR #45) at the cost of one new false trigger, a decline followed by a conditional offer (`call-070`). Not covered: "You can't call me on X" is not a decline pattern and counts as a request |
| 32 | Run-to-run variance of the eval was unmeasured (a full 3B run once differed by one entry on unchanged code) | Low | Measured (§10.7): 5 full runs, 0 pp spread on every aggregate metric, 0 flippers, one answer whose wording varied. The one-entry flip on record is `call-031`, a model-decided entry; not reproduced, not explained |
| 33 | Sprint 4's own end-to-end audit (before merge, `docs/Sprints.md`): a real seed race in `SqliteUserStore` (confirmed with a forced-interleaving reproduction, not hypothetical), a shared-mutable-fixture reference in `MockUserStore`, two style inconsistencies, tests silently writing a real store file despite faking out the graph entirely, and SQLite connections never explicitly closed | Medium (the seed race; the rest low) | All fixed before PR #51 merged. None LLM-facing, so re-verified with the unit suite and a live check rather than a second golden-set run |
| 34 | **A disposable, explicitly-labelled "TEST - DO NOT MERGE" proof PR (deliberately broken to test the Sprint 5 CI gate) was merged into `main` anyway**, because the new `eval-gate` CI check was not yet marked *required* in GitHub branch protection - a check reporting red does not by itself block a merge. For a few minutes `main` served every user the paid knowledge base regardless of tier | High (briefly live on `main`) | Fixed within minutes: caught by checking the actual merge history directly (not a status summary), reverted with one `git revert -m 1` (hotfix PR #55, itself CI-verified green before merging). The same day, `eval-gate` and `test` were both added as required status checks under branch protection (every other existing setting preserved) - the root cause is closed, not just the symptom |
| 35 | `docs/eval/` had grown to 46 report files and kept growing every run, with no accounting for the storage/traceability cost of that growth against the value of keeping every raw run | Low | Decided, not a bug: `docs/eval/` is now gitignored going forward (maintainer decision). Existing files stay on disk and in git history unchanged; only future changes stop being tracked |
| 36 | `.streamlit/` was already blanket-ignored in `.gitignore` (evidently for `secrets.toml`-style local config) - would have silently swallowed Sprint 6's new `config.toml` theme file, the sprint's actual deliverable, with no error or warning | Medium (would have shipped a no-op theme) | Fixed before it shipped: `.gitignore` now excludes only `config.toml` from that directory's blanket rule; `secrets.toml`-style files stay ignored |
| 37 | Sprint 6's theming (`Design.md` §4/§5) was never visually checked in a real browser, in either light or dark mode - no Chrome browser-automation tool was connected in the building session, so only structural presence (via `AppTest`) was verified, not actual color/contrast rendering | Medium | Closed 2026-09-23: rendered in headless Edge in both themes, every text element at WCAG AA or better (§10.11 closeout) |
| 38 | `latest_unfinished()` could return a session other than the one saved last: the Windows clock ticks every 0.5-1 ms, consecutive saves shared `updated_at`, and the rowid tie-break favoured the older row; it surfaced as a flaky test that then blocked commits | Medium | Fixed (#62): each save is stamped strictly after the newest stored time, under a write lock; a frozen-clock test fails without the fix |
| 39 | The 3B model's answers are not byte-stable between runs on this machine: a direct replay of the unchanged prompt gave different answers for 9 of 73 dev questions, two of them new hallucinations, contradicting §10.7's 0-flipper result | Medium (a single run can mislead) | Recorded; round-2 verification ran twice (§10.14) |
| 40 | Using the 3B model to check its own answers against the context is worse than useless: 0 of 4 dev hallucinations flagged, 10-13 of 35 grounded answers flagged | Info | Rejected in favour of deterministic guards (§10.13) |
| 41 | A prompt rule telling the 3B model to state plan restrictions made it tell paid customers their plan did not include things it does, and invent restrictions for free users | Info | Rejected; a deterministic contradiction check used instead (§10.14) |
| 42 | An eval run crashed one entry on an Ollama socket error (Windows buffer exhaustion) | Low | Infrastructure, not code; the entry passed in the second run |

## 14. Challenges Faced

The identity bugs were invisible to manual demoing and to reading the code in isolation — `with_structured_output` constrains the *shape* of a tool-calling model's answer, not whether the model was honest about how it got there, so the bugs looked like ordinary successful turns until checked against a golden-set entry built to break them. Debugging required reading the structured turn log directly rather than trusting the harness's own verdict, since the harness had bugs of its own.

The callback work was the hardest in both sprints. In Sprint 1 the fix was found only by reproducing the pipeline's exact message history, not an approximation of it. In Sprint 2 the trade-off was structural: every wording change that removed false triggers also removed real requests (recall fell to 11%, 82%, 52% and 48% on four alternatives), and the version that kept recall was a deterministic rule ahead of the model, which flatters the entries it was written against. The held-out cohort is what showed how much.

The larger-model experiment had its own traps. The 8B's failures were first read as "the model is worse"; reproducing them showed one mechanism (a tool call written as text) behind identification, fails-safe, retrieval and tier leakage together, which turned a vague negative result into a concrete code gap. Blind hand-grading had to be adjusted mid-way: 19 of 51 questions were asked by premium users the 8B served the free KB, so answers were graded against the KB actually retrieved, with the wrong-tier effect left to the tier-leakage metric. Finally, an intermittent hang in `ident-011` surfaced while verifying the fix; server logs showed a runaway generation with no stop token, unrelated to the change but a real gap (#30).

Sprint 3's challenge was verifying persistence without trusting the tests alone. The store and pipeline tests passed on the first run, which proves little, so they were mutation-checked (breaking six behaviors and confirming each is caught); the resume path was then proved by killing a real process and restarting it. Streamlit could not be opened in a browser, so the app was driven with `AppTest`, which does not refresh its element tree for a rerun made inside a run, so the start-again test checks the session state and runs the script once more. Reading the code for the persistence design also surfaced #37, an old behavior the golden set had never exercised because its entries check only the fail-safe message on the failing turn; the fix added an entry that sends a question after the failure, and it was confirmed to fail on the old code before it was trusted.

Exercising the with-audio path took three attempts. The first install failed in a build step and `pip -q` hid which package, so the workaround was found by trial; the first end-to-end run crashed, so a second, direct probe was needed to show that Whisper itself was fine and that the failure was the ticket step, and that it was deterministic rather than a bad run.

## 15. Limitations

**Still true:** on the shipped `llama3.2:3b` default, held-out callback recall (80%) is below target and the hallucination target is met only on the lenient reading (§10.13) - `gpt-4o-mini` clears the precision target on the same golden set (§10.10), so this is now a limit of the local-model choice, not a limit shown to be inherent to the pipeline; the with-whisper path (real call transcription and ticket summary) works but was exercised only live, twice, on one recording: a single fixed sample is always what is transcribed, so every ticket describes that call, and ticket quality on other calls is unknown; identification is still a lookup, not authentication - a real store now backs it (Sprint 4), but anyone who knows an email or phone number is still served that customer's tier, a decision made deliberately, not just deferred (`docs/User-Store-Design.md`); the code is MIT-licensed but the KB text and call audio are third-party sample data of unconfirmed origin and terms, so their redistribution is unresolved (#14).

**No longer true:** no CI; ruff configured but unenforced (27 findings); the free-tier KB contradicting itself (twice); identification bypassable with fabricated input; no way to reindex the KB deterministically; no held-out data; callback extraction returning the wrong number; a model that skips a tool call getting a made-up tier; phone numbers and mixed-case emails not identifying anyone; no cap or timeout on LLM calls (#30); the README steering users to the rejected 8B model; a conversation being lost on every restart or page reload; a failed identification being followed by free-tier answers (#37); a callback request beside a decline being refused whole (#33); identification backed by an in-memory mock instead of a real, persistent store (Phase 7, Sprint 4); the eval harness's own regression checking depending on a human remembering to run it before merge (Sprint 5's `eval-gate`); OpenAI never having been tried at all (Sprint 6 era, §10.10); `app.py` being a bare, unstyled default Streamlit app (Phase 9, Sprint 6); no accounting for how many tokens a turn costs on either provider.

**New, from Sprint 2:**
- A callback request must include a phone number (maintainer decision, #7); a bare "call me" gets a normal RAG reply.
- All eval numbers are single runs on a 3B model with small n. One answer is 2-7 points on the hallucination sets, and the 22-entry callback cohort has only 12 negatives.
- Hallucination is graded by one reader, and the latest blind grade was done by the same assistant that ran the experiment, not a human. Blinding hides the model, not the reader's judgment; the two most recent grades disagree with the earlier ones (2% vs about 10%), so the absolute rate is uncertain.
- Temperature 0 does not give identical output, but the scored results were stable over five full runs on unchanged code (0 pp on every aggregate metric, no entry changed result; §10.7). The earlier one-entry difference (`call-031`, callback recall 36/37 vs 37/37) was not reproduced and not explained: it is a model-decided entry that has failed once in eleven full 3B runs on record. One answer's wording varied (`rag-free-008`), from the model server and not from retrieval. `ident-011` completed or hung depending on Ollama's state before the #30 bounds.
- Prompts, guards and patterns were developed around 3B behavior, which favors it in any comparison with another model.

**New, since Sprint 3:**
- A decline followed by a conditional offer to be called ("call me back only if the email bounces") now starts a callback (`call-070`, the price of #33), and "You can't call me on X" is not a decline pattern, so it counts as a request too. Full-set precision is 93.6% (44/47), and the new cohort is 12 entries labelled by the author of the fix.

**New, from Sprint 3:**
- Saved conversations hold the user's name, email and phone number in the clear in `data/sessions.sqlite` (gitignored), and the Streamlit session id in the URL is a bearer token: anyone with the link can read the conversation. Acceptable for a local single-instance app; to be re-decided before any real deployment (Phase 10). Sessions are kept until deleted by hand. The turn log (`logs/turns.jsonl`, gitignored) also stores each raw user message.
- Resume trusts the saved profile, tier included; identification is not re-run, so a tier change in the user store mid-session is not seen until the session ends.
- Not exercised: a real browser session, and several processes writing the same database at once (out of scope for the sprint).

**New, from Sprint 4:**
- `data/users.sqlite` (gitignored) now holds the same four sample users' names, emails and phone numbers in the clear that used to live only in source - the privacy posture is the same as `sessions.sqlite` already had, just a second file with the same shape of data.
- Matching (case-insensitive email, digits-only phone) is done in Python after a full-table select, not in SQL - a deliberate simplification for a four-row table (`docs/User-Store-Design.md`), not tested at any larger scale.
- Not built: a second identification factor, decided against for this sprint, not just skipped (`docs/User-Store-Design.md` decision 2).

**New, from Sprint 5:**
- The 14-entry `eval_gate.py` subset is curated for tier-leakage and callback coverage, not statistically representative of the full 135-entry set - a regression outside those categories could pass the gate and still be caught only by the manual full-run step in the PR template.
- The gate compares against a checked-in baseline (`tests/eval/ci_baseline.json`) rather than a metric floor; updating that baseline is a manual step a PR author could get wrong in either direction (silently accepting a regression, or blocking on a false one), and nothing currently checks the baseline itself against the full golden set.
- The incident (finding 34) shows the gate needed branch-protection wiring, not just a green/red signal, to actually bind - a lesson that likely generalizes to any future required check added the same way.

**New, from the OpenAI comparison:**
- One run per backend (§10.10), same caveat as every other model comparison in this report (§10.5, §10.7).
- Compared the chat model only - embeddings stayed on local Ollama for both runs, so this is not evidence about an all-OpenAI stack.
- `gpt-4o-mini`'s callback-precision win (98% vs 94%) is measured on the same golden set the local model's own fixes were developed against over several sprints - it's a fairer comparison than Sprint 1's uninformative 100%, but still not a cohort OpenAI had no prior exposure to in this codebase's history.
- `OPENAI_MODEL` in `.env.example` still defaults to `gpt-3.5-turbo`, a model this comparison never actually ran (`gpt-4o-mini` was used instead, deliberately, as the cheaper and better-performing choice) - the default itself is now known-stale, not just unexercised.

**New, from Sprint 6:**
- Dark mode is Streamlit's own built-in palette, not `Design.md`'s dark column - a real capability limit in Streamlit 1.39.0's `config.toml` (one static custom theme), not an oversight.
- `st.success`/`st.warning` use Streamlit's built-in alert colors, not `Design.md`'s exact success/warning hex codes - chosen over custom CSS per the design doc's own stated preference.
- Sessions saved before 2026-09-23 replay their ticket confirmations as plain text (their replies carry no node); newer ones keep the styling.
- An OS-level dark preference is ignored while a custom theme is set; dark mode is only reachable through Streamlit's settings menu. In light mode the retry warning (4.66:1) and tier badge (4.57:1) pass WCAG AA by a small margin.

**New, from 2026-09-23:**
- #5 and #23 miss their targets on the round-2 held-out cohort (§10.14): callback recall 77% and precision 91%, hallucination 10%. The cohorts are small (13 requests, 11 fired, 20 answers), one grader wrote and graded them, and both rounds' cohorts are now used.
- The deterministic guards are heuristics tuned on a handful of examples: they can refuse a partly right answer (two dev cases) and cannot see a failure that uses no tell-tale wording. The model still refuses many free-tier trap questions instead of stating the restriction.
- Answers vary between runs (§13 finding 39), so any single-run figure in this report carries that uncertainty.
- The live end-to-end checks of §10.2 were not repeated after the 2026-09-23 changes; those changes were exercised through the full golden set (three runs) and the unit tests.
- The sample-call script (`scripts/generate_sample_call.ps1`) runs on Windows only; the old third-party files remain in git history.

**New, from the process evaluation** (`docs/Process-Evaluation.md`; one reviewer's judgment, plan not adopted):
- Retrieval recall@4 on a 14 to 15 chunk index retrieves 27% to 29% of the corpus, so its 100% says little about retrieval quality.
- There is no dependency lockfile (an unpinned `posthog` already broke chromadb's telemetry), no prompt-injection tests, and no real users; the knowledge base is four files per tier, so results will not generalize to a production store.
- Docs and eval reports are far larger than the source, and the same facts live in several files, which is how the audit found stale counts.

## 16. Future Improvements

**Quick:** #14 and #17 are done (§10.12, §10.13). #5 and #23 remain open after two rounds (§10.14); the decision left is whether to accept them as known limits of `llama3.2:3b` or change the model for the steps that miss. The one concrete gap finding 34 (§13) left open - `eval-gate`/`test` as required status checks - was closed the same day, not left for later (`docs/Git-Workflow.md`).

**Medium:** a third round of rules is not recommended: two rounds show each rule closes its own failures while fresh cohorts find new ones. If #5 and #23 must reach target, the measured option is a stronger model for the answer and callback-intent steps (`gpt-4o-mini` cleared callback precision on the full set, §10.10), verified on a new cohort; a second-pass grounding check by the 3B model itself is ruled out (§13 finding 40). The run-to-run difference was measured (§10.7); for a CI gate, flag entries whose result changed and re-run only those, instead of a metric threshold.

**Process (proposed, not adopted; full plan in `docs/Process-Evaluation.md`):** an evidence bundle first (dev, validation and frozen test splits; intervals on every rate; a run manifest and results index per eval), then a smoke-eval gate before merge, independent review of eval labels and metric-affecting PRs, one source per fact with a generated status block, a threat model with a lockfile, and a small real-user trial.

**Larger:** Sprints 4 through 6 (Phases 7-9: real user store, CI regression gate, UI polish) are all done; **Sprint 7 (Phase 10, deployment & observability) is the only sprint left on the roadmap** - containerizing the app, structured metrics beyond console output (latency per node, the token/cost tracking this update's `TokenUsageCallbackHandler` makes possible, error rates), a post-launch monitoring plan, and a lightweight feedback loop for bad answers. The process evaluation suggests a real-user trial may deserve to come before or alongside it.

### Three-bullet summary

- The product (Phases 1-5) already worked before this engagement; it is now *provably* measured and every sprint on the roadmap through Sprint 6 is done — a 237-conversation golden set, 513 unit tests, a CI regression gate that is now a *required* status check, conversations that survive a restart, a real persistent user store, a themed UI, and held-out entries committed before each run — and was re-exercised live on `main` (7 of 7 checks, before the 2026-09-23 changes, which were exercised through three full golden-set runs). The sample data is now original and MIT (#14).
- Three identity bypass or fabrication bugs, a wrong-number callback bug, two KB contradictions, and a real incident where a disposable "do not merge" proof PR still reached `main` (caught and closed within minutes, and the process gap it exposed fixed the same day) were found and fixed, most only because the evaluation and its own gate were built adversarially; retrieval recall (100%) and tier leakage (0%) held at target throughout every sprint since, and Sprint 6's UI work confirmed a full regression run with 0 of 135 entries changed.
- Two quality rounds with held-out cohorts committed before any fix closed #17 (invented steps: 0 of 22) and raised round-1 callback recall to 93%, but on the second fresh cohort (§10.14) the shipped `llama3.2:3b` still misses callback recall (77% vs ≥90%), callback precision (91% vs ≥95%) and hallucination (10% vs ≤5%); rules have not converged on these targets for this model. A larger local model was tried and did not help; **a real, token-measured comparison against OpenAI's `gpt-4o-mini` did** - it cleared the precision target on the full golden set for about three cents - narrowing "known limit" to a cost of staying local rather than a ceiling on the pipeline itself. The only sprint left on the roadmap is deployment and observability (Sprint 7).

### One-line description

A graph-orchestrated, fully-local-by-default LLM customer support agent whose original build was sound but unmeasured — this engagement built the evaluation infrastructure that measured it, fixed the real bugs and one live-traffic incident it exposed, made conversations survive a restart, gave it a real user store, a themed UI and original sample data, measured a real alternative backend against it, and reports honestly which accuracy targets the shipped small local model still does not reach, which of those a paid one does, and how far the evidence can be trusted.
