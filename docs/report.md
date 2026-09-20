# Graph-Orchestrated LLM Customer Support Agent — Project Report

**Repository:** melvinmathew9991/customer-support-app (`main`, with every sprint and fix branch merged and kept)
**Stack:** Python 3.10.10 · Streamlit 1.39.0 · LangChain 0.3.7 (+ langchain-community/-ollama/-openai/-chroma/-text-splitters) · ChromaDB 0.5.20 · pydantic-settings 2.6.1 · pytest 8.3.3 · ruff 0.7.4 · Ollama (local: `llama3.2:3b` chat, `nomic-embed-text` embeddings). Dependencies are unchanged since the initial commit (`pyproject.toml` was never modified); Python and ruff versions were re-checked at the end of Sprint 2, the rest are as pinned.
**Status:** End of Sprint 3 (session persistence), following Sprint 2 (knowledge base and retrieval hardening) and the end-to-end audit whose findings were fixed before that sprint was tagged (`docs/eval/Sprint2-Audit-2026-09-20.md`). Core product (Phases 1-5) was built before this engagement; Sprint 1 built the evaluation foundation and Sprint 2 used it to fix what it exposed. Sprint 2's definition of done is met (retrieval recall and tier leakage held at target on a 3x larger set), but **two accuracy targets are not met**: hallucination (about 13% on untuned questions vs ≤5%) and callback precision (83% on a held-out cohort vs ≥95%). The larger local model was tried and did not help. The maintainer accepted carrying both as known limits on 2026-09-20 rather than continuing to tune them in Sprint 2 (`docs/Sprints.md`).
**Timeline:** 2026-09-18 → 2026-09-20, single contributor (Melvin Mathew). 58 commits and 16 merged pull requests on `main` at the Sprint 2 close-out (#32), plus three small PRs after it: the audit's final fixes (#34), the milestone docs fix (#35) and the CLI and telemetry fixes (#36), then Sprint 3's session persistence (#38). Pre-Sprint-1 (MVP baseline + out-of-band fixes) → Sprint 1 (evaluation foundation, PRs #1-#3) → git workflow tooling (PR #4) → Sprint 2 (PRs #15, #18-#21, #24-#28, #31, #32, #34-#36) → Sprint 3 (session persistence, PR #38).

**Update cadence:** this file is refreshed at the end of each sprint (see `docs/Sprints.md`'s cross-cutting rules) so it always reflects the project's current, verified state rather than a point-in-time snapshot.

---

## 1. Overview & Purpose

A LangChain customer support agent whose conversation flow is modeled as an explicit graph (`Node`/`Edge` framework in `graph/`) instead of a freeform agent, so behavior at each stage is constrained and predictable: `GreetingNode` (identify the user) → `AuthenticatedUserNode` (answer from a tier-selected RAG knowledge base) → `CallCustomerNode` (detect and route callback requests into a ticket). Runs fully local by default via Ollama — no API key required; OpenAI is available as an opt-in but has not been exercised.

The product itself (Phases 1-5) was already built and unit-tested when this engagement began. The work covered here is what came after: running it end-to-end outside its original development context, building the evaluation infrastructure Sprint 0's retrospective had flagged as the project's one real gap (Sprint 1), and then using that infrastructure to fix the failures it exposed and to test, honestly, which of them a larger model would remove (Sprint 2).

## 2. Use Case & Objectives

Primary use case: a tiered (free/paid) e-commerce support chatbot that identifies a customer, answers from a knowledge base scoped strictly to their subscription tier, and can hand off to a human callback when asked — while being *provably* measurable, not just demoable.

Objectives, as they currently stand:

- Identify a user from a natural-language email/phone message and resolve their subscription tier — done. Three fabrication or bypass bugs were found and fixed along the way (§13 findings 6, 7, 20). Phone numbers and mixed-case emails identify correctly since the audit fix (#11); before it, the greeting asked for a phone number the lookup could not use.
- Answer support questions grounded only in the user's own tier's knowledge base, with zero cross-tier leakage — done for leakage (0% on 39 scored retrieval cases). **Grounding is not at target:** see the hallucination row below.
- Detect callback requests and route them to a ticketing flow — working, with a caveat that changed in Sprint 2: recall is 97% (36/37) and precision 94.7% (36/38) on the full set, but on a 22-entry cohort held out from design, precision is **83%** (target ≥95%). A callback request must include a phone number (a maintainer decision, #7), and the ticket has no transcript-based summary unless the optional `audio` extra is installed.
- Run entirely on a local, free model stack — done (Ollama). A larger local model (`llama3.1:8b`) was tested and rejected (§10.5).
- Make the system's behavior measurable, not just observable — done: every defined metric has a real number (machine-scored on a 122-entry golden set; hallucination hand-graded). The hallucination rate misses its ≤5% target.

## 3. Proposed Solution

A single installable package (`src/customer_support_app/`) plus a thin CLI/Streamlit front end — no service layer, no separate database beyond the embedded Chroma store, no orchestration framework beyond LangChain itself and this project's own small `Node`/`Edge` abstraction.

`graph/` is the reusable control-flow framework (any project could reuse it); `agents/support.py` is the concrete conversation built on top of it; `tools/` wraps the mock user DB, the RAG retriever build/reuse logic, and call transcription; `tests/eval/` is the evaluation harness, sitting alongside the original `tests/` unit suite rather than replacing it. `scripts/reindex_kb.py` rebuilds the knowledge-base index deterministically.

## 4. Project Architecture

| Layer | Module | Lines | Responsibility |
|---|---|---|---|
| Config | `config.py` | 135 | pydantic-settings `Settings`: LLM/embeddings provider, paths, `turn_log_path`, `llm_max_tokens` and `llm_timeout_seconds` (#30), `session_db_path` (Sprint 3); drops chromadb's false "Failed to send telemetry event" error (#13) |
| Logging | `logging_config.py` | 78 | Console logger + structured JSON-line turn logger (`logs/turns.jsonl`) |
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
| Agents | `agents/support.py` | 397 | `GreetingNode`, `UserInfoChainBasedEdge` (identity guards, tier taken from the DB record), `AuthenticatedUserNode`, `CallCustomerEdge` (digit pre-check, do-not-call veto, explicit-request patterns, typed-number check) / `CallCustomerNode` |
| Tools | `tools/user_info_db.py` | 65 | Mock user/subscription DB (email lookup ignores case, phone lookup by digits, #11) |
| Tools | `tools/rag_responder.py` | 161 | `HelpCenterAgent`: idempotent index, stable chunk ids, content-based staleness check |
| Tools | `tools/audio_transcribe.py` | 79 | Whisper-based call transcription; `transcription_available()` lets callers degrade instead of crashing |
| Pipeline | `pipeline.py` | 251 | `CustomerSupportPipeline` orchestration + per-turn structured logging; a model timeout becomes a reply (#30); with a `SessionStore` it saves after every completed turn and can resume a saved conversation by rebuilding the graph (no replay, no model call) |
| Interfaces | `cli.py` | 104 | Terminal chat entrypoint; exits cleanly on end of input or `quit`/`exit` (#12); `--session ID` and `--resume` pick up a saved conversation, nothing resumes implicitly |
| Interfaces | `app.py` | 109 | Streamlit Chat + Graph tabs; the session id lives in the URL (`?session=<id>`), so a reload or server restart resumes; an ended conversation shows its transcript and a start-again button |
| UI | `ui/graph_renderer.py` | 55 | Graphviz DAG rendering |
| Scripts | `scripts/reindex_kb.py` | — | Rebuild the Chroma index from `assets/` (`--tier`, `--check`) |
| Tests | `tests/**/test_*.py` | 2,185 | 304 tests across 18 files — deterministic graph/domain/config/agent/reindex/lookup/timeout/CLI/persistence logic and the Streamlit app driven headlessly (no live model) |
| Eval | `tests/eval/` | — | `golden_set.json` (122 hand-labeled conversations, 11 categories), `run_eval.py` (automated scoring harness), `README.md` (schema) |
| CI / tooling | `.github/workflows/ci.yml`, `.githooks/pre-commit`, `.github/pull_request_template.md` | — | pytest + `ruff check` blocking on every PR; local pre-commit test hook |
| Docs | `docs/*.md` + `docs/eval/*.md` | — | PRD, Architecture, Rules, Phases, Design, Persistence-Design, Sprints, Git-Workflow, Metrics, and 34 dated eval/experiment reports |

**2,337** total lines across `src/customer_support_app/`.

## 5. Folder Structure

```
.
├── README.md
├── .env.example / .env (gitignored) / .gitignore
├── pyproject.toml
├── .github/               # workflows/ci.yml, pull_request_template.md
├── .githooks/pre-commit   # runs pytest when src/, tests/ or pyproject.toml change
├── docs/
│   ├── PRD.md, Architecture.md, Rules.md, Design.md, Git-Workflow.md, Persistence-Design.md
│   ├── Phases.md            # what's built, phase by phase, with dated bugfix notes
│   ├── Sprints.md           # the SDLC plan + live status of each sprint
│   ├── report.md            # this file
│   └── eval/                # Metrics.md + 34 dated baseline, held-out, fix-verification, audit and experiment reports
├── scripts/reindex_kb.py
├── src/customer_support_app/
│   ├── config.py, logging_config.py, session_store.py, pipeline.py, cli.py, app.py
│   ├── agents/support.py
│   ├── domain/           # chat.py, graph.py, validation.py
│   ├── graph/             # the reusable Node/Edge framework
│   ├── tools/              # user_info_db.py, rag_responder.py, audio_transcribe.py
│   └── ui/graph_renderer.py
├── tests/                 # 304 unit tests (deterministic logic only)
│   └── eval/               # golden_set.json, run_eval.py, README.md
├── assets/                # free/ + paid/ knowledge base .txt files, sample call audio
├── notebooks/             # legacy exploratory prototype
├── logs/                  # gitignored - logs/turns.jsonl, structured per-turn output
├── data/                  # gitignored - data/sessions.sqlite, saved conversations (holds names, emails, phone numbers in the clear)
└── chroma_db/             # gitignored - persisted vector store
```

## 6. End-to-End Workflow

1. `GreetingNode` asks for an email/phone number.
2. `UserInfoChainBasedEdge` (tool-calling agent over `tools/user_info_db.py`) resolves a `UserProfile`. **Four guards must all pass before a match is trusted:** (a) the user lookup tool must have run and returned a non-empty result (an email, matched ignoring case, or a phone number, matched by digits, #11); (b) the value it was called with must appear in the user's own message, compared by digits for phone numbers (closes a bug where the model invented a lookup argument that matched a real account); (c) the subscription lookup must have run and returned a record (#29: without this, a model that skipped the call had its tier invented by the extractor); (d) the subscription is taken from the DB record itself, and that record must belong to the user who was identified, never from the extractor's reading of the findings. Any failure fails safe with a "couldn't verify your account" reply.
3. `AuthenticatedUserNode` (`RetrievalNode`) answers from Chroma, with the retriever chosen deterministically by `UserProfile.subscription`. The answer prompt requires the model to use only the retrieved context and to say the topic isn't covered otherwise; `invents_steps()` replaces an answer containing UI navigation wording absent from the retrieved context with the not-covered reply. `HelpCenterAgent` reuses a populated collection and warns at startup if the index is out of date with `assets/`.
4. Every LLM call is bounded (`LLM_MAX_TOKENS`, `LLM_TIMEOUT_SECONDS`); a timeout inside a turn becomes a "took too long, please try again" reply and the conversation stays on the same node (#30). Every turn emits a structured JSON-line record (`logs/turns.jsonl`) — node transitions, retrieved doc sources + similarity scores, tool calls made, latency — the raw material the eval harness scores against.
5. `CallCustomerEdge` decides whether the user asked to be called, in this order: no phone number (6+ digits) in the latest message → reject; a "don't call" or "no need to call" phrasing → reject; a plain request ("call me", "give me a call", "someone should phone", "callback") → accept, all without the model; otherwise the LLM intent check decides, shown only user/assistant messages, with a short condition that mentioning, giving, changing or asking about a number is not a request. The number it will call must appear in the user's own message; if the model mis-copies it and the message holds exactly one number, that number is used. If it fires, `CallCustomerNode` produces a ticket from a Whisper transcription when the optional `audio` extra is installed, and otherwise replies that the callback was logged, with no ticket summary.
6. With a `SessionStore` (the CLI and the Streamlit app pass one), the conversation is saved after every completed turn: the message history, the current node's name and typed input, the retry counters of the identity and callback edges, and the conversation id. Given a session id the store holds, the pipeline rebuilds the graph, restores that state and skips the greeting; nothing is replayed and no model is called. A saved row that cannot be resumed (unknown node, wrong input type for its node, bad counters, or a failed identification) starts a new conversation with a warning. Without a store nothing changes, which is how the eval harness runs.

## 7. Technologies Used

| Category | Technology | Verified |
|---|---|---|
| App runtime | Streamlit 1.39.0 | Launched headless (HTTP 200) in Sprint 1. In Sprint 3 driven headlessly with Streamlit's `AppTest`: 7 unit tests, plus a live two-process resume check against the real model. Not launched in a browser since Sprint 1 |
| Orchestration | LangChain 0.3.7 (+ -community/-ollama/-openai/-chroma/-text-splitters) | Exercised live throughout |
| Session store | SQLite (standard library `sqlite3`) | 22 store tests, including migration rollback and a newer-schema refusal; a live kill-and-resume check. No new dependency, no ORM |
| Vector store | ChromaDB 0.5.20 | Reindex script, stable chunk ids and staleness check verified on the real index (free 14 / paid 15 chunks, ids unique) |
| Chat model | Ollama `llama3.2:3b` (local, default) | Exercised across the 122-entry golden set and every experiment |
| Chat model (tested, not adopted) | Ollama `llama3.1:8b` | Full 122-entry run + targeted experiments; rejected (§10.5) |
| Embeddings | Ollama `nomic-embed-text` (local) | Exercised |
| Chat model (opt-in) | OpenAI via `langchain-openai` | Not exercised — no API key configured |
| Audio/transcription | `openai-whisper` (optional `audio` extra) | **Not installed.** The app degrades gracefully without it; the with-whisper path (real transcription + ticket) has never been exercised (#10) |
| Testing | pytest 8.3.3 | 304/304 pass |
| Lint | ruff 0.7.4 | 0 findings (27 fixed in Sprint 2, #9), including `ruff check .` since the legacy notebook was excluded; a blocking CI gate. `ruff format` is not enforced (19 files would change) |
| CI | GitHub Actions (`ci.yml`) | pytest + `ruff check src tests scripts`, both blocking on PRs and pushes to `main`; green on the last merged PR |
| Version control | git + GitHub (`melvinmathew9991/customer-support-app`) | 58 commits, 16 merged PRs at the close-out merge (#32), plus #34-#36 and the Sprint 3 PR (#38); merge commits, branches kept as history, tags `v0.1.0-sprint1` and `v0.1.0-sprint2` (`docs/Git-Workflow.md`) |

## 8. Implementation Details

**Before Sprint 1 and in Sprint 1** (unchanged; details in `docs/Phases.md` and the Sprint 1 reports):

- **Environment repair:** the `.venv`'s editable install pointed at a stale path; `customer_support_app` failed to import at all until reinstalled.
- **RAG indexing made idempotent:** `HelpCenterAgent._create_index` re-embedded on every start (126/135 duplicate chunks, 12MB after repeated runs, versus 14/15 chunks and 7MB fresh).
- **Identification hardened against two fabrication bugs**, both found by building and running the golden set: garbage/unmatched input produced a schema-valid fabricated `UserProfile`, and a sharper variant let an unrelated message authenticate as a real user through an invented lookup argument.
- **Structured per-turn logging** and an **automated eval harness** (`tests/eval/run_eval.py`) built from scratch; three harness bugs found and fixed mid-way.
- **Whisper crash fixed** (degrades to an honest "callback logged" reply), and **callback recall root-caused** (an internal system message leaking into the intent classifier's prompt) and fixed with system-message exclusion plus a digit pre-check.

**Sprint 2 (this report's addition):**

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
- **End-to-end audit and final fixes** (`docs/eval/Sprint2-Audit-2026-09-20.md`): the sprint's claims held and the live metrics reproduced. The audit found and fixed: a README that recommended the rejected 8B model; the lookup not supporting the phone numbers the greeting asks for (**#11**); no cap or timeout on LLM calls (**#30**); a "no need to call me" phrasing that started a callback; a swallowed exception in the retrieval log; and stale docs. It left open the license (#14, a legal decision) and a compound-phrasing callback case (**#33**).

**Sprint 3 (session persistence):**

- **Design first** (`docs/Persistence-Design.md`): what a conversation is made of (history, current node, the node's typed input, retry counters, conversation id), a SQLite store with one JSON row per session, opt-in on the pipeline so the eval harness and the existing tests are untouched, save after every completed turn, load by rebuilding rather than replaying, and four decisions the maintainer answered before any code (SQLite; explicit `--session`/`--resume` only; a finished conversation shows its transcript and says it ended; sessions kept until deleted by hand).
- **Built:** `SessionStore`, save and resume in `CustomerSupportPipeline`, CLI `--session`/`--resume`, Streamlit resume through `?session=<id>`, the `SESSION_DB_PATH` setting, a gitignored `data/` folder. 60 new tests (244 → 304), all without a model. The store and pipeline tests were mutation-checked: removing the counter, id, history or input restore, the save, or the resumable-input check each fails a test.
- **Verified live** against `llama3.2:3b`: CLI started, user identified, question asked, process killed, `--resume` replayed the transcript, did not ask to identify again and answered a follow-up from the premium KB; the Streamlit app opened in a fresh process on the same URL redrew the 5 saved messages with no second greeting and highlighted `AuthenticatedUserNode`. A full 122-entry golden-set run on the branch matches the previous run on every metric.
- **Found and not fixed (#37):** after identification fails the bot says it could not verify the user but keeps answering from the free KB. The persistence design refuses to resume such a session.

## 9. Methodology — Build History

58 commits and 16 merged pull requests at the close-out merge, plus three small PRs after it. By pull request:

| PR | What it did |
|---|---|
| — | Sprint 0 MVP baseline (graph framework, identification, tiered RAG, call-me flow, Streamlit/CLI, 17 unit tests) plus two out-of-band fixes: stale editable install, Chroma duplicate-embedding bug |
| #1, #2, #3 | Sprint 1: eval metrics and targets, golden set (12 → 38), structured logging, automated harness, both identification auth-bypass fixes, harness fixes, whisper and callback-recall fixes, first hallucination grade |
| #4 | Git workflow tooling: CI, pre-commit hook, PR template, line endings |
| #15 | Sprint 2: KB rewrite, stricter answer prompt, reindex tooling (hallucination 20% → 6.7% on the tuned set) |
| #18 | 21 held-out `rag-*` entries; untuned hallucination 9.5% |
| #19 | Fix #16 (manual-payments contradiction), block invented UI steps (#17, partial) |
| #20 | Fix all 27 ruff findings; lint is a hard CI gate (#9) |
| #21 | Held-out callback set and stronger scoring (#8); precision 85% |
| #24, #25 | Fix the wrong-number callback (#22); record it in `Sprints.md` |
| #26 | Record the #7 decision (keep the digit pre-check) |
| #27 | Callback precision 67% → 83% on the held-out cohort (#23, not met) |
| #28 | Larger-model experiment: plan, both full runs, results |
| #31 | Identity guard fix (#29), sprint log entry |
| #32 | Sprint 2 close-out and report refresh |
| #34 | End-to-end audit: doc fixes, #11 lookup, #30 bounds, callback veto, retrieval-log warning; tag `v0.1.0-sprint2` |
| #35 | Docs: the accepted limits live in a `Known limits` milestone, not Sprint 3 |
| #36 | CLI exits cleanly on end of input (#12); the false chromadb telemetry error is dropped (#13) |
| #38 | Sprint 3: session persistence (SQLite store, save and resume in the pipeline, CLI `--session`/`--resume`, Streamlit resume by URL) |

The working pattern since Sprint 2: criteria and held-out entries are committed **before** the run, fixes are developed only against entries already in the set, and the untouched cohort is run once afterwards (`docs/Git-Workflow.md`, the `docs/eval/` reports).

## 10. Results

### 10.1 Unit tests and lint

304/304 passing across 18 files — deterministic graph/domain/config/agent/reindex/lookup/timeout/CLI/persistence logic and the Streamlit app driven headlessly, no live model required (30 at the end of Sprint 1; 209 at the Sprint 2 close-out; 237 after the audit fixes; 244 after the CLI and telemetry fixes). `ruff check` reports no findings, including the whole repo since the notebook exclusion, and is blocking in CI (`src`, `tests`, `scripts`).

### 10.2 Live end-to-end verification

Driven directly, not just tested: identification (free and premium), tiered RAG answers, the callback flow, and the full 122-entry golden set through the real pipeline, on both models. The Streamlit app was last launched in a browser in Sprint 1; in Sprint 3 it was driven headlessly with Streamlit's `AppTest` (a fresh-process resume check on the real model).

### 10.3 Eval harness — current state (`docs/eval/Sprint3-Persistence-FullEval-2026-09-20.md`, 122 conversations, 11 categories, `llama3.2:3b`; the numbers reproduced the earlier `Precision-FullEval-2026-09-19.md` run)

| Metric | Now | Target | End of Sprint 1 (38 entries) |
|---|---|---|---|
| Identification success rate | **100%** (n=8: `ident-007` and `ident-010` became scored after #11) | ≥95% clean / ≥80% ambiguous | 100% |
| Fails-safe rate | **100%** (n=5) | 100% | 100% |
| Retrieval recall@k | **100%** (n=39) | ≥90% | 100% (n=12) |
| Tier-leakage rate | **0%** (n=39) | 0% | 0% (n=12) |
| Callback recall | **100%** (37/37; 97% in the earlier run) | ≥90% | 100% (n=7) |
| Callback precision, full set | **94.9%** (37/39; 94.7% in the earlier run) | ≥95% | 100% (n=7) |
| Callback precision, held-out cohort (`call-037`..`058`) | **83%** (10/12) — **misses target** | ≥95% | not measured |
| Phone extraction | **100%** | none | not measured (94% before the #22 fix, on a later 100-entry run) |
| Hallucination rate | see §10.4 — **misses target** | ≤5% | 20% (3/15) |

The callback rows are lower than Sprint 1's, and that is a *better* measurement, not a regression: Sprint 1's three negatives contained no digits, so the digit pre-check rejected them before the model was consulted and they could never fail. Precision only became informative once negatives that contain a number were added. The full-set 94.7% is inflated by entries the callback change was developed on; the held-out 83% is the honest figure. A fresh 3B full run on 2026-09-19 (`Model-Full-llama3-2-3b-2026-09-19.md`) and the audit's two runs scored callback recall 100% against 97% in the earlier full run on the same code, an unexplained small difference. The held-out 83% reproduced exactly, with the same two false triggers (`call-042`, `call-047`).

### 10.4 Hallucination trajectory (hand-graded against the KB text, one reader)

| Grade | Set | Result |
|---|---|---|
| Sprint 1 | 15 `rag-*`, tuned | 20% (3/15) |
| After KB rewrite and prompt | same 15, tuned | 6.7% (1/15) |
| Untuned held-out | 21 new questions | 9.5% (2/21); 14% counting a KB-caused wrong answer |
| After #16/#17 fixes | 15-entry untuned cohort | fabrication 26.7% → 13.3% (2/15) |
| Blind grade, both models | 51 answered `rag-*` (3B) | 1 clear hallucination (2%); 7 (14%) counting borderline answers |

Target ≤5% is not clearly met on any untuned measure. The last row disagrees with the earlier ones (2% vs about 10%): it includes entries the fixes were tuned on, and the grade is one reader's judgment, so the model *comparison* in §10.5 is the safer reading than that absolute rate.

### 10.5 Larger local model (`docs/eval/Model-Experiment-Results-2026-09-20.md`)

`llama3.1:8b` vs `llama3.2:3b`, model only, same code, KB and golden set, criteria and decision rule committed first. **Not sufficient — it fails all three conditions.**

| Condition | Required | 3B | 8B |
|---|---|---|---|
| Held-out callback precision / recall | ≥95% / ≥90% | 83% / 100% | 100% / 80% |
| Clearly hallucinated answers (of 51) | ≥3 fewer | 1 | 1 |
| No regression | all hold | holds | identification 50%, fails-safe 60%, retrieval recall 62%, tier leakage 38% |

The 8B answers "no" to every message in the model-only intent check, so its 100% precision is not judgment; and it writes its second tool call as plain text instead of calling it, so the subscription is never looked up. That exposed the identity guard gap fixed as #29. It is also about 1.3x slower per entry and 4.9 GB against 2.0 GB.

## 11. Evaluation Metrics

| Metric | Value |
|---|---|
| Unit tests passing | 304/304 (18 files) |
| Golden-set size | 122 conversations across 11 categories |
| Held-out sets written before their run | 21 `rag-*`, 16 + 22 callback, 15 for #16/#17, 10 for #22 |
| Identity bypass/fabrication bugs found and fixed | 3 |
| Eval-harness bugs/gaps found and fixed | 3 in Sprint 1, plus a stronger callback scorer in Sprint 2 |
| KB content defects fixed | 2 (#6, #16) |
| Ruff findings | 27 → 0, enforced in CI |
| Retrieval recall / tier leakage | 100% / 0% (n=39) |
| Callback recall / precision (full set) | 97% / 94.7%; held-out cohort precision 83% |
| Hallucination | 13.3% fabrication on an untuned cohort; 2%-14% on the blind 51-answer grade; target ≤5% |
| Issues | 7 open (#5, #10, #14, #17, #23, #33, #37), 11 closed |
| Commits / PRs | 58 commits, 16 merged PRs at the close-out merge, plus #34-#36 and #38; single contributor |

## 12. Result Analysis

The core product meets its target on every machine-scored metric except callback precision on unseen messages, and misses the hallucination target. Sprint 2's central lesson is about measurement: the numbers that looked good were the ones measured on entries the fixes were built against (6.7% hallucination on the tuned 15, 100% callback precision on negatives with no digits), and each honest re-measure on held-out entries came out worse (9.5%, 83%). Committing the held-out entries before running them, and developing fixes only against entries already in the set, is what made the shortfalls visible instead of hidden.

The levers were spent in order of cost. Triage showed generation, not retrieval, was at fault; a stricter prompt and a KB rewrite helped; a deterministic guard removed one failure class; deterministic patterns bought callback precision but every wording change alone lost recall. The last cheap lever, a larger local model, was tested under criteria fixed in advance and did not help: it removed no hallucinations, lowered callback recall, and broke identification. Its failure was itself useful, exposing an identity-guard gap that would have let any model that skips a tool call silently assign a tier, now fixed. What remains is expensive or risky (more patterns that would overfit a 22-entry cohort, or a second-pass grounding check that adds a model call per answer), which is why the maintainer accepted carrying both accuracy targets as known limits rather than continuing to tune them (`docs/Sprints.md`).

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
| 8 | Call-me ticketing crashes (`ModuleNotFoundError: whisper`) without the optional `audio` extra | High | Fixed (degrades to "callback logged"); the with-whisper path remains unexercised (#10) |
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
| 25 | "No need to call me back, my number is ..." started a callback (the do-not-call veto did not know "no need") | Medium | Fixed. The compound case (declines and requests in one sentence) is open (#33) |
| 26 | Public repository with no LICENSE; the KB is Shopify-derived | Medium | Open (#14), left to the maintainer: a legal decision |
| 27 | After three unidentifiable messages the bot says it could not verify the user, then keeps answering from the free KB (confirmed live). Contradicts the PRD; impact limited to the free KB, tier leakage stays 0% | Low | Open (#37). Not caused by persistence; the persistence design does not resume such a session |

## 14. Challenges Faced

The identity bugs were invisible to manual demoing and to reading the code in isolation — `with_structured_output` constrains the *shape* of a tool-calling model's answer, not whether the model was honest about how it got there, so the bugs looked like ordinary successful turns until checked against a golden-set entry built to break them. Debugging required reading the structured turn log directly rather than trusting the harness's own verdict, since the harness had bugs of its own.

The callback work was the hardest in both sprints. In Sprint 1 the fix was found only by reproducing the pipeline's exact message history, not an approximation of it. In Sprint 2 the trade-off was structural: every wording change that removed false triggers also removed real requests (recall fell to 11%, 82%, 52% and 48% on four alternatives), and the version that kept recall was a deterministic rule ahead of the model, which flatters the entries it was written against. The held-out cohort is what showed how much.

The larger-model experiment had its own traps. The 8B's failures were first read as "the model is worse"; reproducing them showed one mechanism (a tool call written as text) behind identification, fails-safe, retrieval and tier leakage together, which turned a vague negative result into a concrete code gap. Blind hand-grading had to be adjusted mid-way: 19 of 51 questions were asked by premium users the 8B served the free KB, so answers were graded against the KB actually retrieved, with the wrong-tier effect left to the tier-leakage metric. Finally, an intermittent hang in `ident-011` surfaced while verifying the fix; server logs showed a runaway generation with no stop token, unrelated to the change but a real gap (#30).

## 15. Limitations

**Still true:** hallucination (about 13% on untuned questions) and held-out callback precision (83%) are below target; the with-whisper path (real call transcription and ticket summary) has never been exercised, so ticket quality with the `audio` extra installed is unknown; the mock DB is a mock (identification is a lookup, not authentication: anyone who knows an email or phone number is served that customer's tier); there is no real user store (Phase 7); OpenAI models were never tested (the new token and timeout bounds are configured for them but unexercised); the repository has no LICENSE (#14).

**No longer true:** no CI; ruff configured but unenforced (27 findings); the free-tier KB contradicting itself (twice); identification bypassable with fabricated input; no way to reindex the KB deterministically; no held-out data; callback extraction returning the wrong number; a model that skips a tool call getting a made-up tier; phone numbers and mixed-case emails not identifying anyone; no cap or timeout on LLM calls (#30); the README steering users to the rejected 8B model. Also no longer true since Sprint 3: a conversation being lost on every restart or page reload.

**New, from Sprint 2:**
- A callback request must include a phone number (maintainer decision, #7); a bare "call me" gets a normal RAG reply.
- All eval numbers are single runs on a 3B model with small n. One answer is 2-7 points on the hallucination sets, and the 22-entry callback cohort has only 12 negatives.
- Hallucination is graded by one reader, and the latest blind grade was done by the same assistant that ran the experiment, not a human. Blinding hides the model, not the reader's judgment; the two most recent grades disagree with the earlier ones (2% vs about 10%), so the absolute rate is uncertain.
- Temperature 0 does not give identical output: a fresh full 3B run differed slightly from the earlier one on the same code, and `ident-011` completed or hung depending on Ollama's state before the #30 bounds (it completed in the audit's post-fix run, which is not proof, since the hang is intermittent). Not investigated.
- Prompts, guards and patterns were developed around 3B behavior, which favors it in any comparison with another model.

**New, from Sprint 3:**
- Saved conversations hold the user's name, email and phone number in the clear in `data/sessions.sqlite` (gitignored), and the Streamlit session id in the URL is a bearer token: anyone with the link can read the conversation. Acceptable for a local single-instance app; to be re-decided before any real deployment (Phase 10). Sessions are kept until deleted by hand.
- Resume trusts the saved profile, tier included; identification is not re-run, so a tier change in the user store mid-session is not seen until the session ends.
- Not exercised: a real browser session, and several processes writing the same database at once (out of scope for the sprint).

## 16. Future Improvements

**Quick:** #14 (license, and whether the Shopify-derived KB stays public: a maintainer decision). #37 (the failed-identification behavior needs a decision). #5, #17, #23 and #33 stay open as accepted known limits (`docs/Sprints.md`).

**Medium:** exercise the with-whisper transcription-to-ticket path once (#10); if hallucination or callback precision must reach target, scope it as its own sprint with a larger pre-committed held-out set (a second-pass grounding check for #5/#17; a labeled callback-intent set large enough to tune without overfitting for #23); investigate the small 3B run-to-run difference.

**Larger:** Sprint 4, Phase 7 (a real user store behind the same function signatures), per `docs/Sprints.md`; then the evaluation regression gate (Sprint 5), UI polish (Sprint 6) and deployment and observability (Sprint 7).

### Three-bullet summary

- The product (Phases 1-5) already worked before this engagement; it is now *provably* measured — a 122-conversation golden set, 304 unit tests, a blocking CI gate, conversations that survive a restart, and held-out entries committed before each run — up from zero offline metrics at the start.
- Three identity bypass or fabrication bugs, a wrong-number callback bug and two KB contradictions were found and fixed, most only because the evaluation was built adversarially; retrieval recall (100%) and tier leakage (0%) held at target throughout.
- Two accuracy targets are still missed with the 3B (an end-to-end audit afterwards reproduced the metrics and fixed its own findings): hallucination (about 13% on untuned questions vs ≤5%) and callback precision on unseen messages (83% vs ≥95%). A larger local model was tried under criteria fixed in advance and did not help, so the maintainer accepted carrying both as known limits.

### One-line description

A graph-orchestrated, fully-local LLM customer support agent whose original build was sound but unmeasured — this engagement built the evaluation infrastructure that measured it, fixed the real bugs it exposed, and reports honestly which accuracy targets a small local model still does not reach.
