# Graph-Orchestrated LLM Customer Support Agent — Project Report

**Repository:** melvinmathew9991/customer-support-app (branches: `main`, `sprint-1`)
**Stack (verified this session):** Python 3.10.10 · Streamlit 1.39.0 · LangChain 0.3.7 (+ langchain-community/-ollama/-openai/-chroma/-text-splitters) · ChromaDB 0.5.20 · pydantic-settings 2.6.1 · pytest 8.3.3 · Ollama (local: `llama3.2:3b` chat, `nomic-embed-text` embeddings)
**Status:** Core product (Phases 1-5) built, running, and unit-tested before this engagement began. This report covers everything since: an environment repair, two out-of-band bug fixes, and Sprint 1 (evaluation foundation) on an unmerged branch. Sprint 1's work is functionally complete: every metric has a real number, callback detection and the ticketing crash are fixed, and hallucination rate is graded at 20% (target ≤5%, not met, not yet addressed). The latest fixes are **uncommitted working-tree changes** on `sprint-1` as of this report.
**Timeline:** 8 commits total (7 real + 1 merge), `main` + `sprint-1`, 2026-09-18 → 2026-09-19, single contributor (Melvin Mathew). Pre-Sprint-1 (2 commits: MVP baseline + out-of-band fixes) → Sprint 1 batch 1 (1 commit, merged via PR #1: metrics, 12-entry golden set, first auth-bypass fix) → Sprint 1 batch 2 (6 commits on `sprint-1`: structured logging, automated harness, a second sharper auth-bypass fix, golden set scaled to 38, two harness bugs fixed, corrected baseline, this report) → uncommitted: whisper-crash fix, callback-recall fix, hallucination grading, harness false-trigger check.

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
- Detect callback requests and route them to a ticketing flow — done: detection recall 100% (n=7) and precision 100% against ≥90% / ≥95% targets, and the flow completes without the optional `audio` extra (§13 findings 3, 8). Two caveats: a callback request must now include a phone number, and the ticket has no transcript-based summary unless the `audio` extra is installed.
- Run entirely on a local, free model stack — done (Ollama).
- Make the system's behavior measurable, not just observable — done: all 6 defined metrics now have a real number (5 machine-scored, hallucination rate manually graded at 20%, which misses its ≤5% target).

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
| Graph framework | `graph/text_based_edge.py` | 86 | `PydanticTextBasedEdge` (condition-check + structured extraction; `check()` now excludes system messages from the history it shows the model) |
| Graph framework | `graph/static_text_node.py` | 32 | Fixed-text node |
| Agents | `agents/support.py` | 310 | `GreetingNode`, `UserInfoChainBasedEdge` (+ two auth-bypass guards added this engagement), `AuthenticatedUserNode`, `CallCustomerEdge` (+ deterministic phone-number guard) / `CallCustomerNode` (+ degrades gracefully without the `audio` extra) |
| Tools | `tools/user_info_db.py` | 49 | Mock user/subscription DB (email-only lookup — no phone lookup despite the prompt advertising one) |
| Tools | `tools/rag_responder.py` | 77 | `HelpCenterAgent`: now reuses a populated Chroma collection instead of re-embedding on every process start |
| Tools | `tools/audio_transcribe.py` | 77 | Whisper-based call transcription; `transcription_available()` lets callers detect a missing `audio` extra instead of crashing (§13 finding 8) |
| Pipeline | `pipeline.py` | 105 | `CustomerSupportPipeline` orchestration + per-turn structured logging |
| Interfaces | `cli.py` | 30 | Terminal chat entrypoint |
| Interfaces | `app.py` | 72 | Streamlit Chat + Graph tabs |
| UI | `ui/graph_renderer.py` | 55 | Graphviz DAG rendering |
| Tests | `tests/**/test_*.py` | 424 | 30 tests across 7 files — deterministic graph/domain/config/agent logic only (no live model) |
| Eval | `tests/eval/` | — | `golden_set.json` (38 hand-labeled conversations), `run_eval.py` (automated scoring harness), `README.md` (schema) |
| Docs | `docs/*.md` + `docs/eval/*.md` | — | PRD, Architecture, Rules, Phases, Design, Sprints, Metrics, 3 dated baseline/grading reports + a post-fix baseline |

**1,639** total lines across `src/customer_support_app/`.

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
│       ├── Baseline-2026-09-19.md   # machine-scored baseline (38 entries), before the callback/whisper fixes
│       ├── Baseline-2026-09-19-post-fixes.md      # current: same 38 entries after the fixes
│       └── Hallucination-Grading-2026-09-19.md    # manual hallucination grade (15 rag-* entries)
├── src/customer_support_app/
│   ├── config.py, logging_config.py, pipeline.py, cli.py, app.py
│   ├── agents/support.py
│   ├── domain/           # chat.py, graph.py, validation.py
│   ├── graph/             # the reusable Node/Edge framework
│   ├── tools/              # user_info_db.py, rag_responder.py, audio_transcribe.py
│   └── ui/graph_renderer.py
├── tests/                 # 30 unit tests (deterministic logic only)
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
5. `CallCustomerEdge` detects a callback request. It fires only if the user's latest message contains a phone number (6+ digits, a deterministic pre-check) and the LLM intent check then agrees; the intent check is shown only user/assistant messages, never internal system messages. If it fires, `CallCustomerNode` produces a ticket from a Whisper transcription when the optional `audio` extra is installed, and otherwise replies that the callback was logged, with no ticket summary (§13 findings 3, 8).

## 7. Technologies Used

| Category | Technology | Verified this engagement? |
|---|---|---|
| App runtime | Streamlit 1.39.0 | Launched headless, served HTTP 200 |
| Orchestration | LangChain 0.3.7 (+ -community/-ollama/-openai/-chroma/-text-splitters) | Installed + exercised live, extensively |
| Vector store | ChromaDB 0.5.20 | Installed + exercised; idempotency bug found and fixed |
| Chat model | Ollama `llama3.2:3b` (local) | Installed + exercised across 38+ live conversations |
| Embeddings | Ollama `nomic-embed-text` (local) | Installed + exercised |
| Chat model (opt-in) | OpenAI via `langchain-openai` | Not exercised — no API key configured |
| Audio/transcription | `openai-whisper` (optional `audio` extra) | **Not installed.** Was the direct cause of Bug 2 (§13 finding 8); the app now degrades gracefully without it. The with-whisper path (real transcription + ticket) has still never been exercised |
| Testing | pytest 8.3.3 | 30/30 passed, re-verified after every code change this engagement |
| Lint | ruff 0.7.4 (configured in `pyproject.toml`) | Run on `src` + `tests`: 27 findings (14 auto-fixable), identical count at the last commit and after this engagement's uncommitted changes, so no new findings were introduced; the existing ones are not fixed and not enforced |
| CI | none | No `.github/workflows` exists |
| Version control | git + GitHub (`melvinmathew9991/customer-support-app`) | Repo did not exist at the start of this engagement — initialized, committed, and pushed as part of it |

## 8. Implementation Details

- **Environment repair:** the `.venv`'s editable install pointed at a stale path from before the project folder was renamed/moved; `customer_support_app` failed to import at all until reinstalled.
- **RAG indexing made idempotent:** `HelpCenterAgent._create_index` previously called `Chroma.from_documents` unconditionally on every instantiation, with no id-based dedup — measured at 126/135 duplicate chunks and 12MB after repeated runs, versus ~14/15 chunks and 7MB fresh. Now reuses a populated collection instead of re-embedding.
- **Identification hardened against two distinct fabrication bugs**, both found via building and running the golden set, not by code review: garbage/unmatched input previously produced a schema-valid but fabricated `UserProfile`; a sharper variant let a single unrelated message ("what's up") authenticate as a real user because the tool-calling agent invented a plausible lookup argument that happened to match an existing account. Fixed by requiring the lookup's own argument to be traceable to the user's actual message, not just requiring the lookup to return *something*.
- **Structured per-turn logging** added from scratch (`logging_config.py`, wired into `pipeline.py`, `graph/chain_based_node.py`, `graph/chain_based_edge.py`) — JSON-line records with node transitions, retrieval sources/scores, tool calls, and latency, normalized to project-relative paths so they compare directly against the golden set's `expected_source_files`.
- **Automated eval harness built from scratch** (`tests/eval/run_eval.py`) — runs the golden set live, scores each entry against its `expected` fields using the structured log, and computes all 5 machine-scored `Metrics.md` metrics as real percentages. Three harness bugs/gaps were found and fixed mid-engagement: a `KeyError` on intentionally open-ended entries; conflating "detection failed" with "detection succeeded, then a separate crash happened" for callback scoring; and out-of-scope entries never being checked for a false callback trigger (found when a fix of mine regressed one, see below). Retrieval entries now also record the model's answer so they can be graded for hallucination.
- **Whisper crash fixed:** `transcription_available()` in `tools/audio_transcribe.py`; `CallCustomerNode` short-circuits to an honest "callback logged" reply, with no fabricated ticket summary, when the `audio` extra isn't installed. Whisper stays optional per `docs/Rules.md`.
- **Callback recall root-caused and fixed (71% → 100%, n=7):** the two misses (`call-001`, `call-008`) were deterministic, not sampling noise. The intent check was shown the full message history including the internal `system: User Info retrieved: ... phone=...` line, which biased the 3B model toward "no" for those phrasings (0/10 with it, 5/5 without). Removing it alone made the classifier over-fire on phone-related questions; rewording the condition only traded one failure for another (net wash on golden and held-out phrasings); a first reworded-condition-only fix regressed `rag-oos-002` into a false callback trigger. The shipped fix combines stripped history with a deterministic pre-check that the user's message contains a phone number. **Behavior change:** a bare "call me" with no number no longer triggers a callback.

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

30/30 passing (7 files) — deterministic graph/domain/config/agent logic, no live model required (17 original + 13 added this engagement for the audio fallback, the system-message exclusion in `check()`, and the phone-number guard). Re-run and confirmed green after every code change made this engagement.

### 10.2 Live end-to-end verification (this engagement)

Driven directly, not just tested: identification (free and premium tiers), tiered RAG answers (confirmed genuinely different, correct content per tier), the Streamlit app (headless launch, HTTP 200), and the callback flow, which now runs end to end without the `audio` extra and ends the conversation instead of crashing (verified live on a real conversation, and across all 10 callback golden entries in the post-fix run).

### 10.3 Eval harness — current baseline (`docs/eval/Baseline-2026-09-19-post-fixes.md`, 38 conversations, 11 categories)

| Metric | Value | Target | Before fixes (`Baseline-2026-09-19.md`) |
|---|---|---|---|
| Identification success rate | **100%** (n=6) | ≥95% clean / ≥80% ambiguous | 100% |
| Fails-safe rate | **100%** (n=5) | 100% | 100% |
| Retrieval recall@k | **100%** (n=12) | ≥90% | 100% |
| Tier-leakage rate | **0%** (n=12) | 0% | 0% |
| Callback recall | **100%** (n=7) | ≥90% | 71% |
| Callback precision | **100%** (n=7) | ≥95% | 100% (n=5) |
| Hallucination rate | **20%** (3/15, manual) — **misses target** | ≤5% | not graded |

Precision's n rose from 5 to 7 because more callback requests now fire, and because out-of-scope questions now count toward it (a fire there is a false trigger). The hallucination grade (`docs/eval/Hallucination-Grading-2026-09-19.md`) is n=15, one run each: `rag-adv-001` and `rag-adv-002` contradict the free-tier KB ("yes, multiple locations"), and `rag-oos-002` asserts unsupported contact channels instead of saying the topic isn't covered (the judgment call; counting only the two contradictions gives 13%). Nine answers were grounded and correct; three were grounded but unresponsive (a quality issue, not counted). The two contradictions (`rag-adv-001/002`) recurred in the post-fix full run; `rag-oos-002`'s second-run answer was only spot-checked.

## 11. Evaluation Metrics

| Metric | Value |
|---|---|
| Unit tests passing | 30/30 |
| Golden-set size | 38 conversations across 11 categories |
| Auth-bypass bugs found and fixed | 2 |
| Eval-harness bugs/gaps found and fixed | 3 |
| RAG index duplication (before fix) | 126/135 chunks, 12MB → 14/15 chunks, 7MB after fix |
| Callback recall | 100% (n=7) now; 71% before the history fix; an apparent 0% before the harness fix |
| Callback precision | 100% (n=7) |
| Hallucination rate | 20% (3/15) vs. ≤5% target — open |
| `.git` size | 3.1MB (as of the last commit) |
| Commits / branches | 8 total, `main` + `sprint-1` (6 ahead, unmerged) + uncommitted working-tree changes |

## 12. Result Analysis

The core product now meets its target on every machine-scored metric, and misses one: the hallucination rate, at 20% against a ≤5% target. The more interesting result is procedural: building the evaluation infrastructure this engagement set out to build didn't just produce a report card — it directly found two real, escalating identity-fabrication bugs and three bugs or gaps in the measurement tooling itself, none of which surfaced from manual demoing or code review. It also changed the diagnosis of the callback problem: what looked like model flakiness ("non-deterministic on identical input", recorded as a finding since Sprint 0) was a deterministic context-bias bug, an internal system message leaking into the classifier's prompt, found only by reproducing the pipeline's exact message history rather than an approximation of it. And it caught a regression in one of this engagement's own fixes: the first version of the callback fix made an out-of-scope question false-trigger, invisible until the harness was extended to check for it.

## 13. Auditing & Validation of Outcomes

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | Stale editable install — `customer_support_app` failed to import at all | High | Fixed |
| 2 | Chroma RAG index re-embedded and duplicated on every process start (no idempotency) | High | Fixed |
| 3 | Callback-intent detection missed genuine requests (71% recall, n=7). Originally recorded as "non-deterministic on identical input"; actually a deterministic bias from the internal `system:` user-profile message being shown to the intent classifier | Medium | Fixed — 100% recall / 100% precision (n=7) via system-message exclusion + a deterministic phone-number pre-check. Behavior change: a callback request must include a number. 100% is measured on the golden set the fix was developed against (plus 10 held-out phrasings that didn't discriminate), so treat it as an upper bound |
| 4 | `ANONYMIZED_TELEMETRY=False` doesn't actually silence chromadb's telemetry warnings, despite the comment claiming it does | Low (cosmetic) | Open, unchanged |
| 5 | CLI has no graceful exit path (`EOFError` on stdin exhaustion) | Low | Open, unchanged |
| 6 | Identification accepted garbage/unmatched input and fabricated a schema-valid `UserProfile` | Critical | Fixed |
| 7 | Sharper variant of #6: a fabricated tool-call argument matched a *real* account, authenticating as that person from unrelated input | Critical | Fixed |
| 8 | Call-me ticketing crashes (`ModuleNotFoundError: whisper`) whenever the optional `audio` extra isn't installed — the flow can't complete even when detection fires correctly | High | Fixed — degrades to an honest "callback logged" reply with no ticket summary. The with-whisper transcription path remains unexercised |
| 9 | Confirmed hallucination (not tier-leakage) on adversarial tier-crossing questions — retrieval stayed correctly scoped, but the model's answer contradicted its own grounded context | Medium | Open — now graded: `rag-adv-001` and `rag-adv-002` both wrongly tell a free user they can have multiple locations (contradicts `assets/free/locations.txt:8`); see finding 13 |
| 10 | Eval harness: `KeyError` crash scoring two intentionally open-ended golden-set entries | Medium | Fixed |
| 11 | Eval harness: callback recall wrongly conflated "detection never fired" with "detection fired, then a separate crash happened" — understated real recall as 0% instead of 71% | Medium | Fixed |
| 12 | Mock DB lookup is case-sensitive and email-only, despite the prompt advertising phone-number identification too | Low | Open — flagged for Phase 7 (real user store), not yet a confirmed production bug since it currently fails safe |
| 13 | Hallucination rate: 3/15 = 20% against a ≤5% target (`docs/eval/Hallucination-Grading-2026-09-19.md`). Concentrated on one fact (free tier = single location, 4/4 location answers were wrong or evasive) plus one ungrounded answer to an uncovered question (`rag-oos-002`). n=15, one run each | Medium | Open — graded but not fixed; candidate fixes (KB wording, stricter prompt, larger model) are listed in the grading doc |
| 14 | Free-tier KB contradicts itself: `assets/free/pos.txt` lines 3 and 7 say you can sell in person with POS, line 21 says a free subscription can't. Contributes to `rag-adv-004`'s miss | Low | Open — content issue, not code |
| 15 | Harness gap: out-of-scope entries had no `final_node` check, so a false callback trigger on `rag-oos-002` (introduced by a first-draft fix) went unreported | Medium | Fixed — such entries now fail on reaching `CallCustomerNode` and count toward callback precision |

## 14. Challenges Faced

The two auth-bypass bugs were both invisible to manual demoing and to reading the code in isolation — `with_structured_output` constrains the *shape* of a tool-calling model's answer, not whether the model was honest about how it got there, so both bugs looked like ordinary successful turns until checked against a golden-set entry that specifically tried to break them. Debugging the second, sharper variant required reading the structured turn log directly rather than trusting the harness's own pass/fail verdict, since the harness's own scoring logic had a bug that was itself masking the true callback-recall number.

The callback-recall fix was the hardest to get right. A probe that approximated the pipeline's message history showed 100% recall for the exact phrasings that were failing in the real pipeline, which pointed away from the cause; only reproducing the pipeline's actual history (with its internal system message) showed 0/10. Then the obvious fixes each failed differently: dropping the system message alone over-fired on phone-related questions, and rewording the condition only traded misses for false triggers. The first fix shipped to the working tree regressed an out-of-scope question, caught only because the result was checked by hand after the harness reported all-green, since the harness had a blind spot for exactly that case. The final answer was a deterministic rule rather than a better prompt, which is the trade-off `docs/Rules.md` already argues for.

## 15. Limitations

**Still true:** no CI configured; ruff configured but not enforced (27 pre-existing findings); hallucination rate is 20% against a ≤5% target and unaddressed; the with-whisper path (real call transcription and ticket summary) has never been exercised, so ticket quality when the `audio` extra is installed is unknown; the free-tier KB contradicts itself on in-person selling.

**No longer true:** package failed to import; RAG index grew unboundedly on every restart; identification could be bypassed with fabricated or unrelated input; no structured logging existed; no automated way to score the system against a labeled set; the callback flow crashed without the `audio` extra; callback recall was below target; hallucination rate had no number.

**New, from this engagement:**
- A callback request must now include a phone number. A bare "call me" no longer triggers the flow; the user gets a normal RAG reply instead.
- Callback recall/precision of 100% (n=7) were measured on the golden set the fix was developed against. Ten held-out phrasings scored 25/25 recall and 0/25 false-fire before and after the fix, so they confirm no regression but can't show the fix generalizes better than the old code. Real-world recall on unseen phrasings is unknown, and any callback phrasing without a number is now excluded by design.
- All eval numbers are single runs on a non-deterministic 3B model with small n.

## 16. Future Improvements

**Quick:** decide whether to keep requiring a phone number for callbacks (see §15) or fall back to the number on file for a bare "call me"; commit and merge `sprint-1` after review; fix the free-tier KB's self-contradiction on in-person selling (§13 #14).

**Medium:** bring the hallucination rate from 20% toward ≤5% (make the tier limit unambiguous in the KB, a stricter quote-the-context prompt, or a larger model), re-scoring against the same 15 entries; install the `audio` extra once and exercise the real transcription-to-ticket path; add a case-insensitive/phone-capable lookup path ahead of Phase 7's real user store; wire `ruff` + the eval harness into a CI workflow (none exists yet); grow the golden set with more held-out callback phrasings so the recall number stops being tuned against its own test set.

**Larger:** Phase 6 (session persistence) and Phase 7 (real user store) per `docs/Phases.md` — both currently blocked behind closing out Sprint 1 first, per the sprint plan's own sequencing rule.

### Three-bullet summary

- The product (Phases 1-5) already worked before this engagement; what changed is that it's now *provably* measured — all 6 defined metrics have a real number from a 38-conversation golden set (5 machine-scored, hallucination rate manually graded), up from zero offline metrics at the start.
- Two critical identity-fabrication bugs were found and fixed, both invisible to manual testing and only caught because the evaluation infrastructure was built deliberately adversarial rather than happy-path-only — plus three bugs or gaps in the evaluation harness itself, caught the same way.
- Callback detection went from 71% to 100% recall (n=7) at 100% precision, and the ticketing crash is fixed, but the "flakiness" behind it turned out to be a deterministic prompt-context bug, and the fix is a deterministic phone-number requirement, which is a behavior change to review. The one metric still off target is hallucination rate, 20% against ≤5%: graded, concentrated on one fact, and not yet addressed.

### One-line description

A graph-orchestrated, fully-local LLM customer support agent whose original build was sound but unmeasured — this engagement built the evaluation infrastructure that measured it, and in doing so found and fixed two real identity-fabrication bugs that no amount of manual demoing had surfaced.
