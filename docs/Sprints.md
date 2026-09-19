# Sprints — SDLC plan

`Phases.md` tracks *what* gets built, in what order. This file is the *how
and when*: 2-week sprints mapped onto a standard SDLC (requirements → design
→ build → test/evaluate → deploy → operate), with the sequencing a senior
data scientist would insist on for an LLM product specifically: **you can't
improve, or safely change, what you haven't instrumented and can't measure.**
That's why Sprint 1 is evaluation infrastructure, not new features — it comes
before Phases 6-10 in `Phases.md`, not after.

Sprint 0 is a retrospective entry recording the SDLC stage the project is
already past (Phases 1-5), so this file is a complete history, not just a
forward plan.

## Sprint 0 (retrospective) — Requirements & MVP build ✅ Done
**SDLC stage:** Requirements → Design → Build (MVP)
- Defined the conversation flow as an explicit graph instead of a freeform
  agent (`PRD.md`, `Architecture.md`).
- Built the Node/Edge framework, identification flow, tiered RAG, call-me
  ticketing, Streamlit/CLI front ends, provider abstraction (Ollama/OpenAI).
- Unit tests for deterministic logic (graph, domain, config).
- **Gap carried forward:** no offline metrics exist for the LLM-dependent
  behavior (identification accuracy, retrieval correctness, tier leakage,
  callback detection) — verified manually per the README. That gap is the
  entire justification for Sprint 1.

---

## Out-of-band fix (2026-09-18) — Environment repair & RAG indexing bugfix
Not part of any planned sprint - logged here so the history stays accurate.
Found via a manual end-to-end run/audit of the Sprint 0 build, ahead of
Sprint 1's formal eval existing.
- Fixed a broken local dev environment: the `.venv` editable install
  pointed at a stale path from before the project folder was renamed/moved,
  so `customer_support_app` failed to import at all.
- Fixed a retrieval-correctness bug (see `Phases.md` Phase 3): the Chroma
  index was rebuilt unconditionally on every process start with no dedup,
  silently accumulating duplicate chunks (measured: 126/135 chunks and 12MB
  after repeated runs, vs. ~14/15 chunks and 7MB fresh).
- Also surfaced, but deliberately **not** fixed here (belongs in Sprint 1
  as a measured metric, not a one-off patch): callback-intent detection
  (`CallCustomerEdge`) is non-deterministic on identical input with
  `llama3.2:3b` - it sometimes fires, sometimes silently falls through to
  the RAG fallback. This is exactly the "callback-intent precision/recall"
  metric Sprint 1 already plans to formalize.
- README updated with the manual `chroma_db/` reindex workaround pending
  Sprint 2's real reindex script.

---

## Sprint 1 (2 weeks) — Evaluation foundation & instrumentation ✅ Done (merged 2026-09-19, PR #3)
**SDLC stage:** Requirements refinement + Test planning (done *before* more
build work, deliberately)
**Goal:** Make the system's behavior measurable before changing it further.

**Status (2026-09-18):**
- ✅ Metrics defined with explicit targets: `docs/eval/Metrics.md`.
- ✅ Golden set structure + 12 draft conversations (one per category):
  `tests/eval/golden_set.json` + `tests/eval/README.md`. Still needs
  scaling to the full 30-50.
- ✅ First baseline run (manual, against the 12 drafted so far):
  `docs/eval/Baseline-2026-09-18.md` — found and fixed a critical
  identification bug (see Phase 2 in `Phases.md`) in the process.
- ✅ Per-turn structured logging: `logging_config.py` now writes JSON-line
  records to `logs/turns.jsonl` for every turn, retrieval call, and
  tool-calling agent invocation - node transitions, retrieved doc sources
  (project-relative, matching `golden_set.json`'s `expected_source_files`
  format) + similarity scores, tool calls made, and latency per event.
  Wired into `pipeline.py`, `graph/chain_based_node.py`, and
  `graph/chain_based_edge.py`.
- ✅ Automated scoring harness: `tests/eval/run_eval.py` runs the golden
  set against the live pipeline, scores each entry against its `expected`
  fields using `logs/turns.jsonl`, and computes the aggregate metrics from
  `docs/eval/Metrics.md` as real numbers. Not a pytest test (same reason
  as the rest of this project's LLM-dependent behavior - slow, needs a
  live Ollama server) - run manually via
  `python tests/eval/run_eval.py --out <report path>`.
- ✅ Real, machine-scored baseline: `docs/eval/Baseline-2026-09-19.md`.
  Identification success 100% (n=3), fails-safe 100% (n=2), retrieval
  recall@k 100% (n=3), tier-leakage 0% (n=3) - all clean now that Bug 1 is
  fixed. **Callback recall: 0% (n=2)**, badly missing its ≥90% target -
  turns the anecdotal flakiness finding into a real number. Hallucination
  rate is still flagged manual-only by design (`Metrics.md` #5).
  Sample sizes are still small (12-entry golden set) - see below.

**Status (2026-09-19):**
- ✅ Golden set scaled from 12 to 38 conversations (all 11 categories,
  weighted toward identification and callback given they're where the
  known issues are) - `tests/eval/golden_set.json`.
- 🐛 Running the scaled set found a **sharper identification bug**: given
  input as unrelated as "what's up," the tool-calling agent called
  `user_info_db_search` with a fabricated argument that matched a *real*
  account, authenticating as that person. The 2026-09-18 fix only checked
  that the lookup returned something, not that its argument came from the
  user's own message. **Fixed** (see Phase 2 in `Phases.md`) and verified
  against the exact exploit sequence plus a happy-path control.
- 🐛 The 38-entry run also exposed two bugs in `run_eval.py` itself, not
  the app: (1) a `KeyError` crash on the two "uncertain by design" entries
  (`ident-007`, `ident-010`) that don't have a fixed `identified_user` to
  score against, and (2) callback recall being wrongly conflated with the
  already-known whisper crash (Bug 2) - the crash logs show the callback
  edge actually fired correctly 5 of 7 times before hitting that separate
  bug, so the harness's 0% recall figure understated real detection
  performance. Not yet fixed.
- ✅ Both harness bugs fixed (`tests/eval/run_eval.py`) and the full
  38-entry set re-run. `docs/eval/Baseline-2026-09-19.md` now reflects the
  real, current state: identification success 100% (n=6), fails-safe 100%
  (n=5), retrieval recall@k 100% (n=12), tier-leakage 0% (n=12) - all
  clean, and `ident-009` (the exact auth-bypass exploit conversation) now
  passes. **Callback recall: 71% (n=7)**, precision 100% (n=5) - the
  harness fix revealed the edge actually fires correctly more often than
  the earlier 0% figure suggested (5/7 fired; those 5 then hit the
  separate whisper crash, Bug 2); only `call-001`/`call-008` are genuine
  detection misses. Callback recall is the one metric still below target.

**Status (2026-09-19, later):**
- ✅ **Bug 2 fixed.** The callback flow now completes without the `audio`
  extra (`transcription_available()` check; honest "callback logged" message,
  no fabricated ticket summary). Verified live and by unit test.
- ✅ **Hallucination rate graded: 3/15 = 20%** (target ≤5%, **not met**).
  `docs/eval/Hallucination-Grading-2026-09-19.md`. Two definite hallucinations
  are the same fact (free tier = single location, `rag-adv-001/002`); the
  third (`rag-oos-002`) is a judgment call. The two contradictions recurred in
  the post-fix full run (the first `rag-oos-002` answer was only spot-checked
  there). Not fixed - candidate fixes are listed in that file.
- ✅ **Callback recall root-caused and fixed: 71% → 100% (n=7).** The misses
  were deterministic, not sampling noise: the internal `system:` user-profile
  line in the message history biased the 3B classifier. Two fixes (see
  `Phases.md` Phase 4): system messages are no longer shown to the intent
  check, and a callback now requires a phone number in the user's message.
  Prompt rewording alone was tried and rejected - it traded recall for
  precision (net wash on golden + held-out phrasings).
- 🐛 A first cut of the fix (reworded condition only) **regressed
  `rag-oos-002`** into a false callback trigger, which the harness missed
  because out-of-scope entries had no `final_node` check. The harness now
  fails an out-of-scope entry that reaches `CallCustomerNode` and counts it in
  callback precision.
- Post-fix full 38-entry run: `docs/eval/Baseline-2026-09-19-post-fixes.md`.
  Callback recall 100% (n=7), precision 100%, no crashes; every other metric
  unchanged and on target.

**Definition of done status:** every metric now has a real number.
Callback recall/precision now meet target. **Hallucination rate (20%) does
not meet its ≤5% target**, and no fix has been attempted, so Sprint 1's
"every metric has a number" criterion is met but the metric itself is an open
quality issue carried into the next sprint. Caveats: callback numbers come from
a 38-entry golden set the fix was developed against (partially mitigated by 10
held-out phrasings, which didn't discriminate), so treat 100% as an upper
bound; sample sizes are still small.

**Backlog:**
- Define the metrics that matter, with explicit targets, e.g.:
  - Identification success rate (correct `UserProfile` extracted per turn budget)
  - Retrieval relevance (recall@k against a labeled Q→doc mapping, per tier)
  - **Tier-leakage rate — target 0%** (paid content ever surfacing to a free
    user, or vice versa) — this is a correctness bug, not a quality metric
  - Callback-intent precision/recall (does `CallCustomerEdge` fire exactly
    when it should)
  - Hallucination rate (answers not grounded in retrieved KB content)
- Build a golden eval set: 30-50 hand-labeled conversations covering happy
  path, ambiguous identification, free vs. paid questions, callback
  requests, and adversarial phrasing (e.g. a free user asking a paid-only
  question).
- Extend `logging_config.py` output to capture, per turn: current node,
  retrieved doc IDs + scores, tool calls made, latency — the raw material
  every later eval and monitoring sprint depends on.
- Run the current system against the golden set once, by hand if needed, to
  record a **baseline score** per metric.

**Deliverables:** `tests/eval/` (or `docs/eval/`) golden set + rubric,
per-turn structured logging, a baseline metrics report committed to the
repo.
**Definition of done:** every metric above has a number, not a vibe.
**Risk:** building the eval set is tedious and tempting to skip — resist
skipping it; every subsequent sprint reuses it.

---

## Sprint 2 (2 weeks) — Knowledge base & retrieval hardening
**SDLC stage:** Data engineering + iterative build
**Goal:** Fix retrieval/content gaps the Sprint 1 baseline exposed.

**Backlog:**
- Triage golden-set failures from Sprint 1: bad retrieval vs. missing KB
  content vs. bad chunking — separate these before "fixing" anything.
- Expand/correct `assets/free` and `assets/paid` content for exposed gaps.
- Add a reindex script/command to rebuild the Chroma collections
  deterministically from `assets/` (content changes shouldn't require
  manually deleting `chroma_db/`).
- Re-run the Sprint 1 eval set; compare against baseline.

**Status (2026-09-19, sprint started on branch `sprint-2`):** tracked as the
`Sprint 2` milestone on GitHub: #5 (hallucination rate), #6 (free-tier KB
contradiction), #7 (callback behavior decision), #8 (held-out callback
phrasings), #9 (ruff findings + lint gate).
- ✅ **Triage done first, as this sprint's plan requires**
  (`docs/eval/Triage-2026-09-19.md`). For all six problem answers from the
  Sprint 1 hallucination grade, the deciding KB sentence was in the top-ranked
  retrieved chunk. **Retrieval and chunking are not the cause; the model
  ignores context it was given (generation).** One KB content defect is
  confirmed (`free/pos.txt` contradicts itself, #6).
- Consequence: the highest-value work is in the answer prompt/generation and
  KB wording, not retriever changes. Retrieval recall@k and tier leakage are
  already at target and must not regress.

**Deliverables:** updated KB content, `scripts/reindex_kb.py` (or similar),
a before/after retrieval-metrics comparison.
**Definition of done:** retrieval recall@k and tier-leakage rate both
improve or stay at target versus the Sprint 1 baseline — never regress
silently.

---

## Sprint 3 (2 weeks) — Session persistence (Phases.md Phase 6)
**SDLC stage:** Design → Build
**Goal:** Conversations survive process/session restarts.

**Backlog:**
- Design a minimal persistence schema for `MessageHistory` + current node
  identity (SQLite for local/dev is enough — don't over-engineer this for a
  single-instance Streamlit app).
- Implement load/save around `CustomerSupportPipeline`, behind the same
  public interface `app.py`/`cli.py` already use.
- Unit tests for persistence round-tripping (no LLM required).

**Deliverables:** persistence layer + migration, tests.
**Definition of done:** killing and restarting the process mid-conversation
resumes at the same node with full history; existing test suite still
passes untouched.
**Risk:** scope creep into a full session-management system — keep it to
"survive a restart," not multi-user concurrency (out of scope until
there's a real deployment target).

---

## Sprint 4 (2 weeks) — Real user store (Phases.md Phase 7)
**SDLC stage:** Build + integration testing
**Goal:** Replace the mock DB without touching conversation logic.

**Backlog:**
- Define the user-store interface as a contract (methods
  `search_user_info`/`search_user_subscription` already imply one) so
  `agents/support.py` never changes when the backing store does.
- Implement the real lookup (API or DB, per whatever the actual storefront
  system is) behind that interface; keep the mock as a `tests/` fixture.
- Contract tests: same test suite runs against both mock and real
  implementations.
- Re-run the Sprint 1 golden set — identification metrics must hold.

**Deliverables:** real user-store adapter, contract tests.
**Definition of done:** swapping implementations is a one-line config
change, not a code change in `agents/`.

---

## Sprint 5 (2 weeks) — Automated evaluation harness & regression gate (Phases.md Phase 8)
**SDLC stage:** Test automation / CI
**Goal:** Turn Sprint 1's manual eval into a repeatable, CI-enforced gate.

**Backlog:**
- Automate running the golden set against the pipeline (accept that this
  needs a live Ollama model in CI, or a small deterministic
  stand-in/cassette-recorded responses — decide explicitly, don't hand-wave
  it).
- Define regression thresholds per metric (e.g. "tier-leakage must stay at
  0%, retrieval recall@k must not drop >5% from the last accepted
  baseline").
- Wire into CI so a PR that regresses a metric fails, the same way a broken
  unit test would.

**Deliverables:** CI eval job, threshold config, updated `Rules.md` entry
requiring eval runs for any prompt/model/KB change.
**Definition of done:** deliberately regressing the free/paid retriever
selection in a test branch causes CI to fail on the tier-leakage check.

---

## Sprint 6 (2 weeks) — UX/design polish (Phases.md Phase 9)
**SDLC stage:** Build (UI) + usability validation
**Goal:** Apply `Design.md`'s theme/typography spec to `app.py`.

**Backlog:**
- `.streamlit/config.toml` theme (palette from `Design.md`).
- Subscription-tier badge/caption once identified.
- Retry-prompt and ticket-confirmation styling per `Design.md`.
- Manual usability pass in both light and dark mode (per `Design.md` §5).

**Deliverables:** themed app, before/after screenshots.
**Definition of done:** every visual element in `Design.md` §4 is present
and checked in both themes; no functional regression (re-run golden set).

---

## Sprint 7 (2 weeks) — Deployment & observability (Phases.md Phase 10)
**SDLC stage:** Deploy + Operate
**Goal:** Ship somewhere real, and be able to tell if it breaks.

**Backlog:**
- Containerize the Streamlit app; document the deployment path.
- Structured logging/metrics beyond console output: latency per node,
  token/cost tracking per provider, error rates.
- Define the **post-launch monitoring plan**: what triggers a re-run of the
  Sprint 1 eval set in production (model swap, KB update, provider change),
  and a cadence for periodic re-evaluation even with no changes (embedding
  drift, query-distribution shift as real users diverge from the golden
  set).
- Lightweight human-feedback loop: a way to flag a bad answer from the UI,
  feeding future golden-set additions.

**Deliverables:** deployed instance, dashboards/alerts, monitoring runbook.
**Definition of done:** a deliberately broken deploy (bad model config) is
caught by monitoring, not by a user complaint.

---

## Cross-cutting rules for every sprint
- **No sprint ships a prompt, model, or KB change without re-running the
  Sprint 1 golden set** once it exists (from Sprint 2 onward) — this is the
  regression safety net for a system where unit tests can't cover
  LLM-dependent behavior.
- **Definition of Ready** for any sprint's backlog item: it references
  which `PRD.md` feature or `Phases.md` phase it serves, and how it'll be
  measured as done (a test, a metric delta, or an explicit manual check).
- **Definition of Done** for any sprint: tests pass (`pytest`), `ruff`
  clean, `Phases.md` status updated, `docs/report.md` refreshed to reflect
  the sprint's outcome (architecture/results/findings tables, not just a
  changelog line), and — from Sprint 5 onward — the CI eval gate is green.
- Sprints are sequential as scoped above (each depends on the eval
  foundation from Sprint 1), but Sprints 3/4 (persistence, user store) and
  Sprint 6 (design) don't depend on each other and can be reordered or
  parallelized if more than one person is working on this.
