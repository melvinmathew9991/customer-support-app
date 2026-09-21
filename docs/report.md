# Graph-Orchestrated LLM Customer Support Agent — Project Report

**Repository:** melvinmathew9991/customer-support-app (`main`, with every sprint and fix branch merged and kept)
**Stack (this verification, project `.venv`):** Python 3.10.10 · Streamlit 1.39.0 · LangChain 0.3.7 (+ langchain-community 0.3.7, -ollama 0.2.0, -openai 0.2.6, -chroma 0.1.4, -text-splitters 0.3.2) · ChromaDB 0.5.20 · pydantic 2.9.2 / pydantic-settings 2.6.1 · graphviz 0.20.3 · pytest 8.3.3 · ruff 0.7.4 · posthog 7.57.0 (transitive, unpinned) · Ollama with `llama3.2:3b` (chat, default), `nomic-embed-text` (embeddings) and `llama3.1:8b` (tested, not adopted). Not installed in the project `.venv`: `openai-whisper`, `sentence-transformers` (Whisper and torch 2.14.0 were installed once in a separate short-path venv to exercise the audio path, §10.6). The dependency pins are unchanged since the initial commit; the only later edit to `pyproject.toml` is the ruff `extend-exclude` for the legacy notebook (#34).
**Status:** Sprints 1-3 are complete and merged, and two issues were fixed afterwards outside any sprint (#37, #33). The graph-orchestrated agent works end to end and was re-exercised live on the merged `main` at #45 (`a60d9f8`) for this update (identification by email and by phone, tier-scoped answers, a callback, a fail-safe that now ends the conversation, and a save-and-resume through the session store; §10.2). 335 unit tests across 19 files pass and lint is clean. A full 135-entry golden-set run on that commit matches the Sprint 3 run on every metric except callback precision on the full set, which is 93.6% (44/47) against 94.9% before, because of one trade-off in the #33 fix (`call-070`, §10.3). **The with-audio call path was exercised for the first time on 2026-09-21 and did not work; both bugs it turned up (#43, #44) are fixed and re-run live** (§10.6). Core product (Phases 1-5) was built before this engagement; Sprint 1 built the evaluation foundation, Sprint 2 used it to fix what it exposed (then an end-to-end audit fixed its own findings), and Sprint 3 made conversations survive a restart; #37 and #33 were fixed afterwards and the with-audio path was exercised. **Two accuracy targets are not met**: hallucination (about 13% on untuned questions vs ≤5%) and callback precision (83% on a held-out cohort vs ≥95%); the larger local model was tried and did not help, and the maintainer accepted both as known limits. A process evaluation (`docs/Process-Evaluation.md`) rated the method strong and the statistics weak; its plan is proposed, not adopted.
**Timeline:** 2026-09-18 → 2026-09-21 (4, 47, 37 and 10 commits on the four days), single contributor (Melvin Mathew). 98 commits and 26 merged pull requests on `main` as of #45 (`a60d9f8`). GitHub numbers issues and PRs together, so the gaps in the PR numbers (#5-#14, #16, #17, #22, #23, #29, #30, #33, #37, #43, #44) are issues. Pre-Sprint-1 (MVP baseline + out-of-band fixes) → Sprint 1 (evaluation foundation, PRs #1-#3) → git workflow tooling (#4) → Sprint 2 (#15, #18-#21, #24-#28, #31, #32) → audit fixes and follow-ups (#34-#36) → Sprint 3, session persistence (#38) → documentation (#39-#41) → post-Sprint-3 fixes: #37 (#42), #33 (#45), and the with-audio path exercised (#46).

**Update cadence:** this file is updated in the same pull request as any change that alters something it states (counts, architecture, behavior, metrics, findings, limitations), and re-verified against the repository at the end of each sprint (see `docs/Sprints.md`'s cross-cutting rules), so it reflects the project's current state rather than a point-in-time snapshot. Counts that name a pull request ("as of #N") describe the repository at that merge.

---

## 1. Overview & Purpose

A LangChain customer support agent whose conversation flow is modeled as an explicit graph (`Node`/`Edge` framework in `graph/`) instead of a freeform agent, so behavior at each stage is constrained and predictable: `GreetingNode` (identify the user) → `AuthenticatedUserNode` (answer from a tier-selected RAG knowledge base) → `CallCustomerNode` (detect and route callback requests into a ticket). Runs fully local by default via Ollama — no API key required; OpenAI is available as an opt-in but has not been exercised. Conversations are saved after every turn, so a closed terminal or a reloaded page resumes where it stopped.

The product itself (Phases 1-5) was already built and unit-tested when this engagement began. The work covered here is what came after: running it end-to-end outside its original development context, building the evaluation infrastructure Sprint 0's retrospective had flagged as the project's one real gap (Sprint 1), using that infrastructure to fix the failures it exposed and to test, honestly, which of them a larger model would remove (Sprint 2), and adding session persistence (Sprint 3).

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

`graph/` is the reusable control-flow framework (any project could reuse it); `agents/support.py` is the concrete conversation built on top of it; `tools/` wraps the mock user DB, the RAG retriever build/reuse logic, and call transcription; `session_store.py` and `pipeline.py` save and resume a conversation; `tests/eval/` is the evaluation harness, sitting alongside the original `tests/` unit suite rather than replacing it. `scripts/reindex_kb.py` rebuilds the knowledge-base index deterministically.

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
| Agents | `agents/support.py` | 416 | `GreetingNode`, `UserInfoChainBasedEdge` (identity guards, tier taken from the DB record), `AuthenticatedUserNode` (final, so the conversation ends, when identification failed, #37), `CallCustomerEdge` (digit pre-check, do-not-call phrasings taken out before a request is looked for #33, explicit-request patterns, typed-number check) / `CallCustomerNode` |
| Tools | `tools/user_info_db.py` | 65 | Mock user/subscription DB (email lookup ignores case, phone lookup by digits, #11) |
| Tools | `tools/rag_responder.py` | 161 | `HelpCenterAgent`: idempotent index, stable chunk ids, content-based staleness check |
| Tools | `tools/audio_transcribe.py` | 48 | Whisper-based call transcription; the ticket is asked for with structured output (#43); `transcription_available()` lets callers degrade instead of crashing |
| Pipeline | `pipeline.py` | 251 | `CustomerSupportPipeline` orchestration + per-turn structured logging; a model timeout becomes a reply (#30); with a `SessionStore` it saves after every completed turn and can resume a saved conversation by rebuilding the graph (no replay, no model call) |
| Interfaces | `cli.py` | 104 | Terminal chat entrypoint; exits cleanly on end of input or `quit`/`exit` (#12); `--session ID` and `--resume` pick up a saved conversation, nothing resumes implicitly |
| Interfaces | `app.py` | 109 | Streamlit Chat + Graph tabs; the session id lives in the URL (`?session=<id>`), so a reload or server restart resumes; an ended conversation shows its transcript and a start-again button |
| UI | `ui/graph_renderer.py` | 55 | Graphviz DAG rendering |
| Scripts | `scripts/reindex_kb.py` | 59 | Rebuild the Chroma index from `assets/` (`--tier`, `--check`) |
| Tests | `tests/**/test_*.py` | 2,365 | 335 tests across 19 files, none needing a live model: agents (`test_call_customer_edge` 47, `test_user_info_edge` 9, `test_call_customer_node` 4, `test_authenticated_user_node` 2), domain (4), graph (`test_retrieval_guard` 14, `test_node` 5, `test_text_based_edge` 3, `test_edge` 2), tools (`test_user_info_db` 16, `test_rag_responder` 8), eval (`test_golden_set` 124, `test_run_eval_scoring` 19), and top level (`test_session_store` 22, `test_pipeline_persistence` 22, `test_cli` 14, `test_config` 12, `test_app_sessions` 7, `test_pipeline_timeout` 1) |
| Eval | `tests/eval/` | 452 (harness) | `golden_set.json` (135 hand-labeled conversations, 11 categories), `run_eval.py` (automated scoring harness), `README.md` (schema) |
| CI / tooling | `.github/workflows/ci.yml`, `.githooks/pre-commit`, `.github/pull_request_template.md` | — | pytest + `ruff check` blocking on every PR; local pre-commit test hook |
| Docs | `docs/*.md` + `docs/eval/*.md` | — | PRD, Architecture, Rules, Phases, Design, Persistence-Design, Process-Evaluation, Sprints, Git-Workflow, Metrics, and 36 dated eval/experiment reports |

**2,325** total lines across `src/customer_support_app/`.

## 5. Folder Structure

```
.
├── README.md
├── .env.example / .env (gitignored) / .gitignore
├── pyproject.toml
├── .github/               # workflows/ci.yml, pull_request_template.md
├── .githooks/pre-commit   # runs pytest when src/, tests/ or pyproject.toml change
├── docs/
│   ├── PRD.md, Architecture.md, Rules.md, Design.md, Git-Workflow.md, Persistence-Design.md, Process-Evaluation.md
│   ├── Phases.md            # what's built, phase by phase, with dated bugfix notes
│   ├── Sprints.md           # the SDLC plan + live status of each sprint
│   ├── report.md            # this file
│   └── eval/                # Metrics.md + 36 dated baseline, held-out, fix-verification, audit and experiment reports
├── scripts/reindex_kb.py
├── src/customer_support_app/
│   ├── config.py, logging_config.py, session_store.py, pipeline.py, cli.py, app.py
│   ├── agents/support.py
│   ├── domain/           # chat.py, graph.py, validation.py
│   ├── graph/             # the reusable Node/Edge framework
│   ├── tools/              # user_info_db.py, rag_responder.py, audio_transcribe.py
│   └── ui/graph_renderer.py
├── tests/                 # 335 unit tests (deterministic logic only)
│   └── eval/               # golden_set.json, run_eval.py, README.md
├── assets/                # free/ + paid/ knowledge base .txt files, sample call audio
├── notebooks/             # legacy exploratory prototype
├── logs/                  # gitignored - logs/turns.jsonl, structured per-turn output
├── data/                  # gitignored - data/sessions.sqlite, saved conversations (holds names, emails, phone numbers in the clear)
└── chroma_db/             # gitignored - persisted vector store
```

## 6. End-to-End Workflow

1. `GreetingNode` asks for an email/phone number.
2. `UserInfoChainBasedEdge` (tool-calling agent over `tools/user_info_db.py`) resolves a `UserProfile`. **Four guards must all pass before a match is trusted:** (a) the user lookup tool must have run and returned a non-empty result (an email, matched ignoring case, or a phone number, matched by digits, #11); (b) the value it was called with must appear in the user's own message, compared by digits for phone numbers (closes a bug where the model invented a lookup argument that matched a real account); (c) the subscription lookup must have run and returned a record (#29: without this, a model that skipped the call had its tier invented by the extractor); (d) the subscription is taken from the DB record itself, and that record must belong to the user who was identified, never from the extractor's reading of the findings. Any failure fails safe with a "couldn't verify your account" reply; once the retries run out (three failed attempts) that reply ends the conversation, because `AuthenticatedUserNode` is final when it holds no `UserProfile` (#37).
3. `AuthenticatedUserNode` (`RetrievalNode`) answers from Chroma, with the retriever chosen deterministically by `UserProfile.subscription`. The answer prompt requires the model to use only the retrieved context and to say the topic isn't covered otherwise; `invents_steps()` replaces an answer containing UI navigation wording absent from the retrieved context with the not-covered reply. `HelpCenterAgent` reuses a populated collection and warns at startup if the index is out of date with `assets/`.
4. Every LLM call is bounded (`LLM_MAX_TOKENS`, `LLM_TIMEOUT_SECONDS`); a timeout inside a turn becomes a "took too long, please try again" reply and the conversation stays on the same node (#30). Every turn emits a structured JSON-line record (`logs/turns.jsonl`) — node transitions, retrieved doc sources + similarity scores, tool calls made, latency — the raw material the eval harness scores against.
5. `CallCustomerEdge` decides whether the user asked to be called, in this order: no phone number (6+ digits) in the latest message → reject; every "don't call" or "no need to call" phrasing is taken out of the message and, if a plain request ("call me", "give me a call", "someone should phone", "callback") remains → accept, all without the model (#33: "never call me before 9am, but do call me on X" counts, "never call me on X" does not); a phrasing was taken out and no request remains → reject; otherwise the LLM intent check decides, shown only user/assistant messages, with a short condition that mentioning, giving, changing or asking about a number is not a request. The number it will call must appear in the user's own message; if the model mis-copies it and the message holds exactly one number, that number is used. If it fires, `CallCustomerNode` is meant to produce a ticket from a Whisper transcription when the optional `audio` extra is installed (the ticket is asked for with structured output, #43), and otherwise, or if the ticket cannot be read, replies that the callback was logged, with no ticket summary.
6. With a `SessionStore` (the CLI and the Streamlit app pass one), the conversation is saved after every completed turn: the message history, the current node's name and typed input, the retry counters of the identity and callback edges, and the conversation id. Given a session id the store holds, the pipeline rebuilds the graph, restores that state and skips the greeting; nothing is replayed and no model is called. A saved row that cannot be resumed (unknown node, wrong input type for its node, bad counters, or a failed identification) starts a new conversation with a warning. Without a store nothing changes, which is how the eval harness runs.

## 7. Technologies Used

| Category | Technology | Verified this update? |
|---|---|---|
| App runtime | Streamlit 1.39.0 | Installed; the real `app.py` is driven headlessly with Streamlit's `AppTest` in 7 unit tests and in a fresh-process resume check on the real model (Sprint 3). **Not launched in a browser since Sprint 1** |
| Orchestration | LangChain 0.3.7 (+ -community/-ollama/-openai/-chroma/-text-splitters) | Exercised live this update (§10.2) |
| Session store | SQLite (standard library `sqlite3`) | 22 store tests, including migration rollback and a newer-schema refusal; a save-and-resume check re-run live this update. No new dependency, no ORM |
| Vector store | ChromaDB 0.5.20 | Index checked against `assets/` this update: free 14 / paid 15 chunks, none stale |
| Chat model | Ollama `llama3.2:3b` (local, default) | Exercised live this update, and across the 135-entry golden set and every experiment |
| Chat model (tested, not adopted) | Ollama `llama3.1:8b` | Installed locally. Not re-run this update; results are from the Sprint 2 full run and targeted experiments (§10.5) |
| Embeddings | Ollama `nomic-embed-text` (local) | Exercised live this update (retrieval) |
| Chat model (opt-in) | OpenAI via `langchain-openai` | Not exercised — no API key configured |
| Audio/transcription | `openai-whisper` (optional `audio` extra) | **Not installed in the project `.venv`.** Installed in separate short-path venvs on 2026-09-21 (`openai-whisper` 20250625 pinned by the extra since #44, `librosa` 0.10.2, torch 2.14.0): Whisper works, the ticket step works (#43), and the extra installs in a fresh venv without a workaround; §10.6. The app degrades gracefully without it |
| Testing | pytest 8.3.3 | 335/335 pass, re-run for #43 and #44 in the fresh audio venv (6.8 s) |
| Lint | ruff 0.7.4 | 0 findings on `src tests scripts` and on the whole repo, re-run this update; a blocking CI gate. `ruff format` is not enforced (20 files would change) |
| CI | GitHub Actions (`ci.yml`) | pytest + `ruff check src tests scripts`, both blocking on PRs and pushes to `main`; 49 of 49 runs green, including the run for #45 |
| Version control | git + GitHub (`melvinmathew9991/customer-support-app`) | 98 commits, 26 merged PRs as of #45; merge commits, branches kept as history, tags `v0.1.0-sprint1` and `v0.1.0-sprint2` (`docs/Git-Workflow.md`); `main` requires a PR and the `test` check |

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

## 9. Methodology — Build History

98 commits and 26 merged pull requests as of #45. By pull request:

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

The working pattern since Sprint 2: criteria and held-out entries are committed **before** the run, fixes are developed only against entries already in the set, and the untouched cohort is run once afterwards (`docs/Git-Workflow.md`, the `docs/eval/` reports).

## 10. Results

### 10.1 Unit tests and lint

335/335 passing across 19 files — deterministic graph/domain/config/agent/reindex/lookup/timeout/CLI/persistence logic and the Streamlit app driven headlessly, no live model required (30 at the end of Sprint 1; 209 at the Sprint 2 close-out; 237 after the audit fixes; 244 after the CLI and telemetry fixes; 304 after Sprint 3; 312 after #37; 333 after #33; 335 after #43). `ruff check` reports no findings, including the whole repo since the notebook exclusion, and is blocking in CI (`src`, `tests`, `scripts`).

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

Limits: five runs, one machine, one night. "0 flippers" is a lower bound on the true range. Wall time was steady at 783-796 s per run. Not tested: attributing a flip (the plan's Phase 2 was skipped because none occurred), warm versus cold model state beyond run 1, or another day. Compare runs with `scripts/summarize_eval_runs.py`.

## 11. Evaluation Metrics

| Metric | Value |
|---|---|
| Unit tests passing | 335/335 (19 files) |
| Live end-to-end checks on merged `main` (#45) | 7/7 pass (identify by email and phone, paid-only and free-only retrieval, callback, fail-safe, resume) |
| CI | 49/49 runs green |
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
| Issues | 4 open (#5, #14, #17, #23), 16 closed once #43 and #44 are closed by their fix |
| Commits / PRs | 98 commits, 26 merged PRs as of #45; single contributor |
| Since Sprint 3 | 4 issues fixed: #37 and #33 (one trade-off), and #43 and #44, the two bugs found by exercising the with-audio path |

## 12. Result Analysis

The core product meets its target on every machine-scored metric except callback precision on unseen messages, and misses the hallucination target. Sprint 2's central lesson is about measurement: the numbers that looked good were the ones measured on entries the fixes were built against (6.7% hallucination on the tuned 15, 100% callback precision on negatives with no digits), and each honest re-measure on held-out entries came out worse (9.5%, 83%). Committing the held-out entries before running them, and developing fixes only against entries already in the set, is what made the shortfalls visible instead of hidden.

The levers were spent in order of cost. Triage showed generation, not retrieval, was at fault; a stricter prompt and a KB rewrite helped; a deterministic guard removed one failure class; deterministic patterns bought callback precision but every wording change alone lost recall. The last cheap lever, a larger local model, was tested under criteria fixed in advance and did not help: it removed no hallucinations, lowered callback recall, and broke identification. Its failure was itself useful, exposing an identity-guard gap that would have let any model that skips a tool call silently assign a tier, now fixed. What remains is expensive or risky (more patterns that would overfit a 22-entry cohort, or a second-pass grounding check that adds a model call per answer), which is why the maintainer accepted carrying both accuracy targets as known limits rather than continuing to tune them (`docs/Sprints.md`).

Sprint 3 changed the product's shape, not its accuracy: persistence is opt-in on the pipeline, so the eval harness runs exactly as before and every metric held, and the live checks confirm a saved conversation resumes at the same node. The process evaluation adds a caution about the numbers themselves: at these sample sizes several targets cannot be confirmed either way (held-out callback precision of 10/12 has a 95% interval of 55% to 95%; hallucination of 2/15 has 4% to 38%), so the honest reading of "target not met" is "not shown to be met", and the next gain in trust comes from more and better-separated test data, not more tuning.

The work after Sprint 3 repeated the same lessons in miniature. #37 sat unmeasured because every identification entry checked the fail-safe message on the failing turn and none checked the turn after it; the fix added an entry that sends a question after the failure, and it was confirmed to fail on the old code before it was trusted. #33 shows the #23 trade-off again: taking declines out of the message recovered all five compound requests on a cohort committed first, and cost one conditional case (`call-070`) that was labelled before the change and was not tuned away, so full-set precision moved from 95.1% to 93.6% on one entry. And exercising the with-audio path found a deterministic crash that had been invisible for as long as the extra stayed optional: "a callback works" was true only without it.

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
| 26 | Public repository with no LICENSE; the KB is Shopify-derived | Medium | Open (#14), left to the maintainer: a legal decision |
| 27 | After three unidentifiable messages the bot says it could not verify the user, then keeps answering from the free KB (confirmed live on 2026-09-20). Contradicts the PRD; impact limited to the free KB, tier leakage stays 0% | Low | Fixed (#37, PR #42): the fail-safe message now ends the conversation. Not caused by persistence. New golden-set entry `ident-014` fails on the old code and passes now; §10.2 conversation C |
| 28 | Process (`docs/Process-Evaluation.md`): targets cannot be confirmed at the sample sizes used, the golden set has been reused across about 15 runs, eval runs carry no manifest (git SHA, model digest, settings), the 20 PRs measured had 0 reviews, and docs plus eval reports are about 9 times the source | Medium | Open. A ten-point plan is proposed, not adopted; suggested first step is one PR for data splits, interval reporting and run manifests |
| 29 | With the `audio` extra installed, a callback request crashes the conversation: the 3B returns the ticket's JSON schema instead of a ticket (identical on two runs at temperature 0) and the exception is uncaught. Found by exercising the path for the first time (§10.6) | High for that configuration (an optional extra) | Fixed (#43): structured ticket, plus a fallback to the "callback logged" reply if a ticket cannot be read |
| 30 | Installing the `audio` extra into a fresh venv fails on `pkg_resources` in a source build; it worked with `setuptools<70` and `--no-build-isolation` | Low | Fixed (#44): the extra pins `openai-whisper==20250625`, which builds in a fresh venv |
| 31 | The do-not-call veto refused a message that declines one call and requests another ("Never call me before 9am, but do call me on X") | Medium | Fixed (#33, PR #45) at the cost of one new false trigger, a decline followed by a conditional offer (`call-070`). Not covered: "You can't call me on X" is not a decline pattern and counts as a request |
| 32 | Run-to-run variance of the eval was unmeasured (a full 3B run once differed by one entry on unchanged code) | Low | Measured (§10.7): 5 full runs, 0 pp spread on every aggregate metric, 0 flippers, one answer whose wording varied. The one-entry flip on record is `call-031`, a model-decided entry; not reproduced, not explained |

## 14. Challenges Faced

The identity bugs were invisible to manual demoing and to reading the code in isolation — `with_structured_output` constrains the *shape* of a tool-calling model's answer, not whether the model was honest about how it got there, so the bugs looked like ordinary successful turns until checked against a golden-set entry built to break them. Debugging required reading the structured turn log directly rather than trusting the harness's own verdict, since the harness had bugs of its own.

The callback work was the hardest in both sprints. In Sprint 1 the fix was found only by reproducing the pipeline's exact message history, not an approximation of it. In Sprint 2 the trade-off was structural: every wording change that removed false triggers also removed real requests (recall fell to 11%, 82%, 52% and 48% on four alternatives), and the version that kept recall was a deterministic rule ahead of the model, which flatters the entries it was written against. The held-out cohort is what showed how much.

The larger-model experiment had its own traps. The 8B's failures were first read as "the model is worse"; reproducing them showed one mechanism (a tool call written as text) behind identification, fails-safe, retrieval and tier leakage together, which turned a vague negative result into a concrete code gap. Blind hand-grading had to be adjusted mid-way: 19 of 51 questions were asked by premium users the 8B served the free KB, so answers were graded against the KB actually retrieved, with the wrong-tier effect left to the tier-leakage metric. Finally, an intermittent hang in `ident-011` surfaced while verifying the fix; server logs showed a runaway generation with no stop token, unrelated to the change but a real gap (#30).

Sprint 3's challenge was verifying persistence without trusting the tests alone. The store and pipeline tests passed on the first run, which proves little, so they were mutation-checked (breaking six behaviors and confirming each is caught); the resume path was then proved by killing a real process and restarting it. Streamlit could not be opened in a browser, so the app was driven with `AppTest`, which does not refresh its element tree for a rerun made inside a run, so the start-again test checks the session state and runs the script once more. Reading the code for the persistence design also surfaced #37, an old behavior the golden set had never exercised because its entries check only the fail-safe message on the failing turn; the fix added an entry that sends a question after the failure, and it was confirmed to fail on the old code before it was trusted.

Exercising the with-audio path took three attempts. The first install failed in a build step and `pip -q` hid which package, so the workaround was found by trial; the first end-to-end run crashed, so a second, direct probe was needed to show that Whisper itself was fine and that the failure was the ticket step, and that it was deterministic rather than a bad run.

## 15. Limitations

**Still true:** hallucination (about 13% on untuned questions) and held-out callback precision (83%) are below target; the with-whisper path (real call transcription and ticket summary) works but was exercised only live, twice, on one recording: a single fixed sample is always what is transcribed, so every ticket describes that call, and ticket quality on other calls is unknown; the mock DB is a mock (identification is a lookup, not authentication: anyone who knows an email or phone number is served that customer's tier); there is no real user store (Phase 7); OpenAI models were never tested (the token and timeout bounds are configured for them but unexercised); the repository has no LICENSE (#14).

**No longer true:** no CI; ruff configured but unenforced (27 findings); the free-tier KB contradicting itself (twice); identification bypassable with fabricated input; no way to reindex the KB deterministically; no held-out data; callback extraction returning the wrong number; a model that skips a tool call getting a made-up tier; phone numbers and mixed-case emails not identifying anyone; no cap or timeout on LLM calls (#30); the README steering users to the rejected 8B model; a conversation being lost on every restart or page reload; a failed identification being followed by free-tier answers (#37); a callback request beside a decline being refused whole (#33).

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

**New, from the process evaluation** (`docs/Process-Evaluation.md`; one reviewer's judgment, plan not adopted):
- Retrieval recall@4 on a 14 to 15 chunk index retrieves 27% to 29% of the corpus, so its 100% says little about retrieval quality.
- There is no dependency lockfile (an unpinned `posthog` already broke chromadb's telemetry), no prompt-injection tests, and no real users; the knowledge base is four files per tier, so results will not generalize to a production store.
- Docs and eval reports are far larger than the source, and the same facts live in several files, which is how the audit found stale counts.

## 16. Future Improvements

**Quick:** #14 (license, and whether the Shopify-derived KB stays public: a maintainer decision). #5, #17 and #23 stay open as accepted known limits (`docs/Sprints.md`).

**Medium:** if hallucination or callback precision must reach target, scope it as its own sprint with a larger pre-committed held-out set (a second-pass grounding check for #5/#17; a labeled callback-intent set large enough to tune without overfitting for #23). The run-to-run difference was measured (§10.7); for a CI gate, flag entries whose result changed and re-run only those, instead of a metric threshold.

**Process (proposed, not adopted; full plan in `docs/Process-Evaluation.md`):** an evidence bundle first (dev, validation and frozen test splits; intervals on every rate; a run manifest and results index per eval), then a smoke-eval gate before merge, independent review of eval labels and metric-affecting PRs, one source per fact with a generated status block, a threat model with a lockfile, and a small real-user trial.

**Larger:** Sprint 4, Phase 7 (a real user store behind the same function signatures), per `docs/Sprints.md`; then the evaluation regression gate (Sprint 5), UI polish (Sprint 6) and deployment and observability (Sprint 7). The process evaluation suggests the eval gate and a real-user trial may deserve to come before the real user store.

### Three-bullet summary

- The product (Phases 1-5) already worked before this engagement; it is now *provably* measured — a 135-conversation golden set, 333 unit tests, a blocking CI gate, conversations that survive a restart, and held-out entries committed before each run — and was re-exercised live on the merged `main` for this update (7 of 7 checks).
- Three identity bypass or fabrication bugs, a wrong-number callback bug and two KB contradictions were found and fixed, most only because the evaluation was built adversarially; retrieval recall (100%) and tier leakage (0%) held at target throughout, Sprint 3 changed nothing on any metric, and the two fixes since (#37, #33) held every metric except callback precision on the full set (one new false trigger, `call-070`). The one path never measured, the with-audio ticket, turned out to be broken.
- Two accuracy targets are still missed with the 3B: hallucination (about 13% on untuned questions vs ≤5%) and callback precision on unseen messages (83% vs ≥95%). A larger local model was tried under criteria fixed in advance and did not help, so the maintainer accepted carrying both as known limits. A process evaluation found the method strong and the statistics weak (several targets cannot be confirmed at the sample sizes used) and proposed a plan that is not yet adopted.

### One-line description

A graph-orchestrated, fully-local LLM customer support agent whose original build was sound but unmeasured — this engagement built the evaluation infrastructure that measured it, fixed the real bugs it exposed, made conversations survive a restart, and reports honestly which accuracy targets a small local model still does not reach and how far the evidence can be trusted.
