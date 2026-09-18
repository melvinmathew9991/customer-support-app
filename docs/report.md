# Graph-Orchestrated LLM Customer Support Agent — Project Report

**Repository:** melvinmathew9991/customer-support-app (branches: `main`, `sprint-1`)
**Stack (verified this session):** Python 3.10.10 · Streamlit 1.39.0 · LangChain 0.3.7 (+ langchain-community/-ollama/-openai/-chroma/-text-splitters) · ChromaDB 0.5.20 · pydantic-settings 2.6.1 · pytest 8.3.3 · Ollama (local: `llama3.2:3b` chat, `nomic-embed-text` embeddings)
**Status:** Core product (Phases 1-5) built, running, and unit-tested before this engagement began. This report covers everything since: an environment repair, two out-of-band bug fixes, and Sprint 1 (evaluation foundation) now substantially complete on an unmerged branch.
**Timeline:** 8 commits total (7 real + 1 merge), `main` + `sprint-1`, 2026-09-18 → 2026-09-19, single contributor (Melvin Mathew). Pre-Sprint-1 (2 commits: MVP baseline + out-of-band fixes) → Sprint 1 batch 1 (1 commit, merged via PR #1: metrics, 12-entry golden set, first auth-bypass fix) → Sprint 1 batch 2 (5 commits, currently open on `sprint-1`: structured logging, automated harness, a second sharper auth-bypass fix, golden set scaled to 38, two harness bugs fixed, corrected final baseline).

**Update cadence:** this file is refreshed at the end of each sprint (see `docs/Sprints.md`'s cross-cutting rules) so it always reflects the project's current, verified state rather than a point-in-time snapshot.

---

## 1. Overview & Purpose

A LangChain customer support agent whose conversation flow is modeled as an explicit graph (`Node`/`Edge` framework in `graph/`) instead of a freeform agent, so behavior at each stage is constrained and predictable: `GreetingNode` (identify the user) → `AuthenticatedUserNode` (answer from a tier-selected RAG knowledge base) → `CallCustomerNode` (detect and route callback requests into a ticket). Runs fully local by default via Ollama — no API key required; OpenAI is available as an opt-in.

The product itself (Phases 1-5) was already built and unit-tested when this engagement began. The work covered here is what came after: running it end-to-end for the first time outside its original development context, auditing it, and building the evaluation infrastructure Sprint 0's own retrospective had flagged as the project's one real gap — no offline metrics existed for any LLM-dependent behavior.

## 2. Use Case & Objectives

Primary use case: a tiered (free/paid) e-commerce support chatbot that identifies a customer, answers from a knowledge base scoped strictly to their subscription tier, and can hand off to a human callback when asked — while being *provably* measurable, not just demoable.

Objectives, as they currently stand:

- Identify a user from a natural-language email/phone message and resolve their subscription tier — done, but see §13 findings 6-7 for two auth-bypass bugs found and fixed en route.
- Answer support questions grounded only in the user's own tier's knowledge base, with zero cross-tier leakage — done, 0% tier-leakage across 12 scored retrieval cases.
- Detect callback requests and route them to a ticketing flow — partially done: detection recall is 71% against a ≥90% target, and the ticketing step itself has an unfixed crash (§13 finding 8).
- Run entirely on a local, free model stack — done (Ollama).
- Make the system's behavior measurable, not just observable — done: 5 of 6 defined metrics now have a real, machine-scored number; the 6th (hallucination rate) is intentionally manual but not yet actually graded.

## 3. Proposed Solution

A single installable package (`src/customer_support_app/`) plus a thin CLI/Streamlit front end — no service layer, no separate database beyond the embedded Chroma store, no orchestration framework beyond LangChain itself and this project's own small `Node`/`Edge` abstraction.

`graph/` is the reusable control-flow framework (any project could reuse it); `agents/support.py` is the concrete conversation built on top of it; `tools/` wraps the mock user DB, the RAG retriever build/reuse logic, and call transcription; `tests/eval/` is the evaluation harness added this engagement, sitting alongside the original `tests/` unit suite rather than replacing it.

## 4. Project Architecture

| Layer | Module | Lines | Responsibility |
|---|---|---|---|
| Config | `config.py` | 108 | pydantic-settings `Settings`: LLM/embeddings provider, paths, `turn_log_path` |
| Logging | `logging_config.py` | 78 | Console logger + structured JSON-line turn logger (`logs/turns.jsonl`, added this engagement) |
| Domain | `domain/chat.py` | 64 | `MessageHistory`, `Role`, `model_input()` |
| Domain | `domain/graph.py` | 21 | `MessageOutput`, `EdgeOutput` |
| Domain | `domain/validation.py` | 28 | `UserProfile`, `PhoneCallRequest`, `PhoneCallTicket`, `Validation` |
| Graph framework | `graph/node.py` | 68 | `BaseNode`: `run_to_continue`, `execute` |
| Graph framework | `graph/edge.py` | 89 | `BaseEdge`: parse/retry/exhaustion lifecycle |
| Graph framework | `graph/chain_based_node.py` | 129 | `RetrievalNode` (RAG + retrieval logging), `MultifunctionNode` |
| Graph framework | `graph/chain_based_edge.py` | 157 | `ZeroShotChainBasedEdge` (tool-calling agent; now exposes raw intermediate tool-call steps, not just a flattened summary) |
| Graph framework | `graph/text_based_edge.py` | 79 | `PydanticTextBasedEdge` (condition-check + structured extraction) |
| Graph framework | `graph/static_text_node.py` | 32 | Fixed-text node |
| Agents | `agents/support.py` | 282 | `GreetingNode`, `UserInfoChainBasedEdge` (+ two auth-bypass guards added this engagement), `AuthenticatedUserNode`, `CallCustomerEdge`/`Node` |
| Tools | `tools/user_info_db.py` | 49 | Mock user/subscription DB (email-only lookup — no phone lookup despite the prompt advertising one) |
| Tools | `tools/rag_responder.py` | 77 | `HelpCenterAgent`: now reuses a populated Chroma collection instead of re-embedding on every process start |
| Tools | `tools/audio_transcribe.py` | 70 | Whisper-based call transcription — hard `import whisper` with no optional-dependency guard (§13 finding 8) |
| Pipeline | `pipeline.py` | 105 | `CustomerSupportPipeline` orchestration + per-turn structured logging |
| Interfaces | `cli.py` | 30 | Terminal chat entrypoint |
| Interfaces | `app.py` | 72 | Streamlit Chat + Graph tabs |
| UI | `ui/graph_renderer.py` | 55 | Graphviz DAG rendering |
| Tests | `tests/*.py` | 263 | 17 tests across 4 files — deterministic graph/domain/config logic only |
| Eval | `tests/eval/` | — | `golden_set.json` (38 hand-labeled conversations), `run_eval.py` (automated scoring harness), `README.md` (schema) |
| Docs | `docs/*.md` + `docs/eval/*.md` | — | PRD, Architecture, Rules, Phases, Design, Sprints, Metrics, 2 dated baseline reports |

**1,597** total lines across `src/customer_support_app/`.

## 5. Folder Structure

```
.
├── README.md
├── .env.example / .env (gitignored) / .gitignore
├── pyproject.toml
├── docs/
│   ├── PRD.md, Architecture.md, Rules.md, Design.md
│   ├── Phases.md            # what's built, phase by phase, with dated bugfix notes
│   ├── Sprints.md           # the SDLC plan + live status of each sprint
│   ├── report.md            # this file
│   └── eval/
│       ├── Metrics.md               # the 5 eval metrics, formulas, targets
│       ├── Baseline-2026-09-18.md   # first manual baseline (12 entries)
│       └── Baseline-2026-09-19.md   # current machine-scored baseline (38 entries)
├── src/customer_support_app/
│   ├── config.py, logging_config.py, pipeline.py, cli.py, app.py
│   ├── agents/support.py
│   ├── domain/           # chat.py, graph.py, validation.py
│   ├── graph/             # the reusable Node/Edge framework
│   ├── tools/              # user_info_db.py, rag_responder.py, audio_transcribe.py
│   └── ui/graph_renderer.py
├── tests/                 # 17 unit tests (deterministic logic only)
│   └── eval/               # golden_set.json, run_eval.py, README.md - added this engagement
├── assets/                # free/ + paid/ knowledge base .txt files, sample call audio
├── notebooks/             # legacy exploratory prototype
├── logs/                  # gitignored - logs/turns.jsonl, structured per-turn output
└── chroma_db/             # gitignored - persisted vector store (now idempotent across restarts)
```

## 6. End-to-End Workflow

1. `GreetingNode` asks for an email/phone number.
2. `UserInfoChainBasedEdge` (tool-calling agent over `tools/user_info_db.py`) resolves a `UserProfile`. **Two guards added this engagement, both required before trusting a match:** (a) the DB lookup tool must have actually been called and returned a non-empty result — closes the original fabricate-an-empty-profile bug; (b) the value the tool was called *with* must actually appear in the user's own message — closes a sharper bug where the model called the lookup tool with a fabricated argument that happened to match a real account.
3. `AuthenticatedUserNode` (`RetrievalNode`) answers from Chroma, retriever chosen deterministically by `UserProfile.subscription`. `HelpCenterAgent` now checks whether the tier's collection is already populated before re-embedding, instead of rebuilding it on every process start.
4. Every turn now also emits a structured JSON-line record (`logs/turns.jsonl`) — node transitions, retrieved doc sources + similarity scores, tool calls made, latency — the raw material the eval harness scores against.
5. `CallCustomerEdge` detects a callback request; if it fires, `CallCustomerNode` is meant to produce a ticket, but currently crashes on an unmet optional dependency (`whisper`) before it can (§13 finding 8).

## 7. Technologies Used

| Category | Technology | Verified this engagement? |
|---|---|---|
| App runtime | Streamlit 1.39.0 | Launched headless, served HTTP 200 |
| Orchestration | LangChain 0.3.7 (+ -community/-ollama/-openai/-chroma/-text-splitters) | Installed + exercised live, extensively |
| Vector store | ChromaDB 0.5.20 | Installed + exercised; idempotency bug found and fixed |
| Chat model | Ollama `llama3.2:3b` (local) | Installed + exercised across 38+ live conversations |
| Embeddings | Ollama `nomic-embed-text` (local) | Installed + exercised |
| Chat model (opt-in) | OpenAI via `langchain-openai` | Not exercised — no API key configured |
| Audio/transcription | `openai-whisper` (optional `audio` extra) | **Not installed** — this is the direct cause of Bug 2 (§13 finding 8) |
| Testing | pytest 8.3.3 | 17/17 passed, re-verified after every code change this engagement |
| Lint | ruff 0.7.4 (configured in `pyproject.toml`) | Configured but not run this engagement |
| CI | none | No `.github/workflows` exists |
| Version control | git + GitHub (`melvinmathew9991/customer-support-app`) | Repo did not exist at the start of this engagement — initialized, committed, and pushed as part of it |

## 8. Implementation Details

- **Environment repair:** the `.venv`'s editable install pointed at a stale path from before the project folder was renamed/moved; `customer_support_app` failed to import at all until reinstalled.
- **RAG indexing made idempotent:** `HelpCenterAgent._create_index` previously called `Chroma.from_documents` unconditionally on every instantiation, with no id-based dedup — measured at 126/135 duplicate chunks and 12MB after repeated runs, versus ~14/15 chunks and 7MB fresh. Now reuses a populated collection instead of re-embedding.
- **Identification hardened against two distinct fabrication bugs**, both found via building and running the golden set, not by code review: garbage/unmatched input previously produced a schema-valid but fabricated `UserProfile`; a sharper variant let a single unrelated message ("what's up") authenticate as a real user because the tool-calling agent invented a plausible lookup argument that happened to match an existing account. Fixed by requiring the lookup's own argument to be traceable to the user's actual message, not just requiring the lookup to return *something*.
- **Structured per-turn logging** added from scratch (`logging_config.py`, wired into `pipeline.py`, `graph/chain_based_node.py`, `graph/chain_based_edge.py`) — JSON-line records with node transitions, retrieval sources/scores, tool calls, and latency, normalized to project-relative paths so they compare directly against the golden set's `expected_source_files`.
- **Automated eval harness built from scratch** (`tests/eval/run_eval.py`) — runs the golden set live, scores each entry against its `expected` fields using the structured log, and computes all 5 `Metrics.md` metrics as real percentages. Two bugs in the harness itself were found and fixed mid-engagement (a `KeyError` on intentionally open-ended entries; conflating "detection failed" with "detection succeeded, then a separate crash happened" for callback scoring).

## 9. Methodology — Build History

8 commits total (7 real + 1 GitHub-merged PR), across `main` and the still-open `sprint-1` branch:

| Commit | Branch | What it did |
|---|---|---|
| `e8a72b9` | `main` | Sprint 0 MVP baseline (graph framework, identification, tiered RAG, call-me flow, Streamlit/CLI, 17 unit tests) plus two out-of-band fixes made before Sprint 1 started: repaired the stale editable install, fixed the Chroma RAG duplicate-embedding bug |
| `860c57d` | `sprint-1` → merged | Defined the 5 eval metrics with targets; drafted a 12-entry golden set (one per category); fixed the first identification auth-bypass; first manual baseline run |
| `e60b890` | merge → `main` | PR #1: `sprint-1` → `main` |
| `1d4a8ff` | `sprint-1` (open) | Structured per-turn JSON logging, wired into pipeline/graph/RAG layers |
| `d35806b` | `sprint-1` (open) | Automated scoring harness; first machine-scored baseline (12 entries) |
| `b92c657` | `sprint-1` (open) | Found and fixed the sharper auth-bypass (fabricated tool-call argument matching a real account); scaled golden set 12 → 38 |
| `eaab7b2` | `sprint-1` (open) | Fixed two bugs in the harness itself (`KeyError` crash; callback-recall/crash conflation) |
| `dd28575` | `sprint-1` (open) | Re-ran the full 38-entry set through the corrected harness — the current, real baseline |

`sprint-1` is 5 commits ahead of `main` as of this report and not yet merged back.

## 10. Results

### 10.1 Unit tests

17/17 passing (`tests/*.py`, 4 files) — deterministic graph/domain/config logic, no live model required. Re-run and confirmed green after every code change made this engagement.

### 10.2 Live end-to-end verification (this engagement)

Driven directly, not just tested: identification (free and premium tiers), tiered RAG answers (confirmed genuinely different, correct content per tier), the Streamlit app (headless launch, HTTP 200), and the callback flow (confirmed the edge fires correctly on real conversations, separately from the ticketing crash).

### 10.3 Eval harness — current baseline (`docs/eval/Baseline-2026-09-19.md`, 38 conversations, 11 categories)

| Metric | Value | Target |
|---|---|---|
| Identification success rate | **100%** (n=6) | ≥95% clean / ≥80% ambiguous |
| Fails-safe rate | **100%** (n=5) | 100% |
| Retrieval recall@k | **100%** (n=12) | ≥90% |
| Tier-leakage rate | **0%** (n=12) | 0% |
| Callback recall | **71%** (n=7) | ≥90% |
| Callback precision | **100%** (n=5) | ≥95% |
| Hallucination rate | not yet graded (manual by design) | ≤5% |

## 11. Evaluation Metrics

| Metric | Value |
|---|---|
| Unit tests passing | 17/17 |
| Golden-set size | 38 conversations across 11 categories |
| Auth-bypass bugs found and fixed | 2 |
| Eval-harness bugs found and fixed | 2 |
| RAG index duplication (before fix) | 126/135 chunks, 12MB → 14/15 chunks, 7MB after fix |
| Callback recall (corrected) | 71% (n=7) — was measured as an apparent 0% before the harness fix |
| `.git` size | 3.1MB |
| Commits / branches | 8 total, `main` + `sprint-1` (5 ahead, unmerged) |

## 12. Result Analysis

The core product works and, on every metric that's actually been measured except callback recall, works cleanly at or above target. The more interesting result is procedural: building the evaluation infrastructure this engagement set out to build didn't just produce a report card — it directly found two real, escalating identity-fabrication bugs and two bugs in the measurement tooling itself, none of which surfaced from manual demoing or code review. The remaining gap (callback recall at 71%, plus the still-crashing ticketing step) is now a precisely bounded, numbers-backed problem instead of an anecdote — exactly the outcome Sprint 1 was scoped to produce.

## 13. Auditing & Validation of Outcomes

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | Stale editable install — `customer_support_app` failed to import at all | High | Fixed |
| 2 | Chroma RAG index re-embedded and duplicated on every process start (no idempotency) | High | Fixed |
| 3 | Callback-intent detection non-deterministic on identical input (llama3.2:3b) | Medium | Open — now quantified: 71% recall (n=7) vs. ≥90% target |
| 4 | `ANONYMIZED_TELEMETRY=False` doesn't actually silence chromadb's telemetry warnings, despite the comment claiming it does | Low (cosmetic) | Open, unchanged |
| 5 | CLI has no graceful exit path (`EOFError` on stdin exhaustion) | Low | Open, unchanged |
| 6 | Identification accepted garbage/unmatched input and fabricated a schema-valid `UserProfile` | Critical | Fixed |
| 7 | Sharper variant of #6: a fabricated tool-call argument matched a *real* account, authenticating as that person from unrelated input | Critical | Fixed |
| 8 | Call-me ticketing crashes (`ModuleNotFoundError: whisper`) whenever the optional `audio` extra isn't installed — the flow can't complete even when detection fires correctly | High | Open |
| 9 | Confirmed hallucination (not tier-leakage) on an adversarial tier-crossing question — retrieval stayed correctly scoped, but the model's answer contradicted its own grounded context | Medium | Open — needs the manual hallucination-rate grading pass |
| 10 | Eval harness: `KeyError` crash scoring two intentionally open-ended golden-set entries | Medium | Fixed |
| 11 | Eval harness: callback recall wrongly conflated "detection never fired" with "detection fired, then a separate crash happened" — understated real recall as 0% instead of 71% | Medium | Fixed |
| 12 | Mock DB lookup is case-sensitive and email-only, despite the prompt advertising phone-number identification too | Low | Open — flagged for Phase 7 (real user store), not yet a confirmed production bug since it currently fails safe |
| 13 | Hallucination rate metric is scoped as manual-only by design but has not yet actually been graded and recorded as a number | Medium | Open — blocks Sprint 1's formal close |

## 14. Challenges Faced

The two auth-bypass bugs were both invisible to manual demoing and to reading the code in isolation — `with_structured_output` constrains the *shape* of a tool-calling model's answer, not whether the model was honest about how it got there, so both bugs looked like ordinary successful turns until checked against a golden-set entry that specifically tried to break them. Debugging the second, sharper variant required reading the structured turn log directly rather than trusting the harness's own pass/fail verdict, since the harness's own scoring logic had a bug that was itself masking the true callback-recall number.

## 15. Limitations

**Still true:** no CI configured; ruff configured but not enforced; the callback ticketing flow cannot complete end-to-end without a manual `audio` extra install; hallucination rate has no real number yet.

**No longer true:** package failed to import; RAG index grew unboundedly on every restart; identification could be bypassed with fabricated or unrelated input; no structured logging existed; no automated way to score the system against a labeled set.

**New, from this engagement:** callback-intent recall is confirmed at 71%, below target — a real, bounded number replacing an earlier anecdotal "seems flaky" impression.

## 16. Future Improvements

**Quick:** fix Bug 2 (gate the whisper import behind the optional extra, or make it a hard dependency and document it as such); do the hallucination-rate manual grading pass over the existing baseline report's answers.

**Medium:** decide whether 71% callback recall is acceptable for a 3B local model or needs a larger model/better prompt; add a case-insensitive/phone-capable lookup path ahead of Phase 7's real user store; wire `ruff` + the eval harness into a CI workflow (none exists yet).

**Larger:** Phase 6 (session persistence) and Phase 7 (real user store) per `docs/Phases.md` — both currently blocked behind closing out Sprint 1 first, per the sprint plan's own sequencing rule.

### Three-bullet summary

- The product (Phases 1-5) already worked before this engagement; what changed is that it's now *provably* measured — 5 of 6 defined metrics have real, machine-scored numbers from a 38-conversation golden set, up from zero offline metrics at the start.
- Two critical identity-fabrication bugs were found and fixed, both invisible to manual testing and only caught because the evaluation infrastructure was built deliberately adversarial rather than happy-path-only — plus two bugs in the evaluation harness itself, caught the same way.
- The one metric still below target, callback-intent recall at 71% against a ≥90% goal, is now a precise, bounded number instead of an anecdote — and it's decoupled from the separate, still-open crash (Bug 2) that was previously masking how often detection actually succeeds.

### One-line description

A graph-orchestrated, fully-local LLM customer support agent whose original build was sound but unmeasured — this engagement built the evaluation infrastructure that measured it, and in doing so found and fixed two real identity-fabrication bugs that no amount of manual demoing had surfaced.
