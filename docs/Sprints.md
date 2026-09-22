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

## Sprint 2 (2 weeks) — Knowledge base & retrieval hardening ✅ Done (closed 2026-09-20, PR #32 and the final-fixes PR #34; tag `v0.1.0-sprint2`)
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
- ✅ **Stricter answer prompt** (`docs/eval/Prompt-Experiment-2026-09-19.md`):
  fixes `rag-oos-002` (uncovered question answered from general knowledge) and
  regresses nothing on the 15-question screen (27/45 -> 30/45). Only a
  partial fix: the location answers and `rag-adv-004` still fail even with a
  strict prompt and only two chunks, so the remaining lever is KB wording.
  Quoting the source sentence and trimming context were tried and rejected.
- ✅ **KB rewrite** (`docs/eval/KB-Rewrite-Results-2026-09-19.md`): free and
  paid `locations.txt` and free `pos.txt` now state each tier's limit
  unambiguously (fixes #6, the `pos.txt` self-contradiction). Full 38-entry
  eval: all six machine-scored metrics identical to Sprint 1 (no regression;
  retrieval recall 100%, tier leakage 0%). **Hand-graded hallucination rate:
  20% -> 6.7% (3/15 -> 1/15), target <=5% still not met.** On five held-out
  questions the old KB got 6/15 right and the new one 12/15. The remaining
  hallucination (`rag-free-002`, mild) is a side effect of the KB change, not
  pre-existing; n=15 is too coarse for a <=5% target (one answer = 6.7%).
- ✅ **`rag-*` golden set grown 15 -> 36** (golden set now 59 entries) with 21
  entries written from the KB text and committed before any run
  (`docs/eval/Rag-HeldOut-Results-2026-09-19.md`). Retrieval recall 100% and
  tier leakage 0% (n=16) hold on the unseen questions. **Hand-graded
  hallucination on the 21 untuned questions: 2/21 = 9.5% (14% counting a
  KB-caused wrong answer), so the earlier 6.7% on the tuned 15 was
  optimistic and the <=5% target is not met.** Failures: invented UI steps
  for "how do I..." questions (`rag-free-006`, `rag-oos-007`) and a KB
  self-contradiction (`free/payments.txt:8` vs `:46`). Not fixed; these
  entries stay held-out only until used to tune.
- ✅/❌ **Fixes for #16 and #17, verified on an untuned test cohort**
  (`docs/eval/Fix-16-17-Verification-2026-09-19.md`; criteria written before the
  fixes, 15 new entries baselined before and run once after). **#16 met:** the
  free `payments.txt` contradiction is fixed and the free tier now answers
  "not allowed" while the paid tier is unaffected. **#17 not met:** prompt rule 5
  plus a deterministic `invents_steps()` guard (navigation wording absent from the
  retrieved context is replaced with the not-covered reply) removed the click-path
  fabrications (4 blocks in the run, all correct, no false positives), but 2 of
  10 procedural test entries still fabricate in ways the guard cannot see
  (`rag-free-012` misattributes "store admin"; `rag-oos-011` describes setup steps
  in plain prose). Fabrication on the untuned cohort: 26.7% -> 13.3%; the <=5%
  target is not met. No regression: machine-scored metrics unchanged (retrieval
  100%, leakage 0%, callbacks 100%/100%), development answers 22/36 identical and
  none worse.
- ✅ **Held-out callback set and stronger scoring (#8)**
  (`docs/eval/Callback-HeldOut-Results-2026-09-19.md`): 16 new entries written and
  committed before any run (golden set 90), plus a scorer that now checks which
  number the bot says it will call. Recall holds (17/17, new 10/10 across varied
  number formats). **Precision does not: 85% vs the >=95% target**, 3 of the 6 new
  hard negatives started a callback (a support number, a profile-number update, an
  SMS-alerts question). The three original negatives contain no digits, so the
  digit pre-check rejects them before the model is consulted and they can never
  fail; Sprint 1's 100% precision was uninformative. **A wrong number surfaced:**
  existing `call-007` had the bot call the profile number instead of the one the
  user typed, invisible to the old scorer. Not fixed; the set is now used.
- ✅ **Wrong-number callback fixed (#22)**
  (`docs/eval/Extraction-Leak-Results-2026-09-19.md`). Cause confirmed: the
  extraction prompt included the internal profile line, so `call-007` returned the
  profile number in 5 of 5 runs. Fix: system messages stay out of extraction, and the
  extracted digits must appear in the user's own message, otherwise the single number
  they typed is used (several numbers: reject). 10 fresh entries were committed before
  any run, but they were already at ceiling (the leak reproduced only on `call-007`),
  so they show no regression, not an improvement. The first version of the fix
  regressed `call-002` (the model mis-copied a digit and the guard blocked the
  call); the typed-number fallback was added after seeing that on a used entry. Full
  eval, 100 entries: **phone extraction 94% -> 100% (26/26)**, recall 96% (26/27),
  precision 90% (26/29, not comparable to 85% since the set gained positives). The 3
  false triggers and `call-033` remain (#23). The 14 unscored entries were read by
  hand and are identical to the last full run.
- ✅/❌ **Callback precision (#23), improved but the target is not met**
  (`docs/eval/Callback-Precision-Results-2026-09-19.md`). A 22-entry cohort was
  committed before any run and held out from design. Every stricter wording alone
  lost recall (as in Sprint 1: 11%, 82%, 52%, 48%); the change that kept it is a
  deterministic accept for plain requests ("call me", "give me a call") and a
  "don't call" veto, ahead of a shorter model condition. **On the untouched
  cohort: precision 67% -> 83% (5 -> 2 false triggers of 12), recall 10/10 both
  times, identical across 3 baseline runs.** Not met (target >=95%): `call-042` is
  still wrong and `call-047` is a new false trigger. Full eval, 122 entries: recall
  97% (36/37), precision 94.7% (36/38, inflated by the entries the change was
  developed on), extraction 100%, other metrics unchanged.
- ✅ **Lint cleanup and hard CI gate (#9).** All 27 ruff findings fixed (12
  import-order, 12 long lines, and one each of unused import, f-string without
  placeholders, and an undefined name that was a forward reference needing a
  `TYPE_CHECKING` import). Verified behavior-neutral by comparing every modified
  file's syntax tree with the previous version, ignoring only import order: 10 of
  13 files identical, and the 3 that differ do so exactly as intended (including
  every re-wrapped user-facing message). 105 tests pass and every module still
  imports. CI's `ruff check src tests scripts` step is now blocking (no
  `continue-on-error`); a deliberate violation exits 1.
- ✅ **Reindex command** (`scripts/reindex_kb.py`, `--tier`, `--check`), stable
  chunk ids, content-based staleness check, and a startup warning when the
  index is out of date. 8 unit tests (fake embeddings, no Ollama); verified on
  the real index (free 14 / paid 15 chunks, ids unique).
- ❌ **Larger local model tried for #5, #17 and #23: not sufficient**
  (`docs/eval/Model-Experiment-Plan-2026-09-19.md`, criteria fixed before the run;
  `docs/eval/Model-Experiment-Results-2026-09-20.md`). `llama3.1:8b` vs `llama3.2:3b`,
  model only, same code/KB/golden set (122 entries), one run each. **The 8B fails all
  three conditions of the decision rule.** Held-out callback (`call-037`..`058`):
  precision 100% but recall 80% (3B: 83% / 100%); the 8B answers "no" to every message
  in the model-only intent check, so its precision is not judgment. Hallucination,
  hand-graded blind on 51 answers: 1 clear hallucination each (needed 3 fewer); the 8B
  refuses far more (20 vs 11), mostly premium users served the wrong KB. Regressions:
  identification 100% -> 50%, fails-safe 100% -> 60%, retrieval recall 100% -> 62%, tier
  leakage 0% -> 38%. Cause: the 8B writes its second tool call
  (`user_subscription_db_search`) as text instead of calling it. Cost: about 1.3x slower
  per entry, 4.9 GB vs 2.0 GB. Caveats: one run per model, one reader who is also the
  assistant that ran it, and the 3B's clear-hallucination rate here (2%) is lower than the
  earlier 9.5% on the same kind of set, so the model comparison is the safer reading.
  **#5, #17 and #23 remain unmet with the 3B** (about 13% fabrication on untuned
  questions vs 5%; callback precision 83% vs 95%).
- ✅ **Identity guard now requires the subscription lookup (#29)**, found by the
  experiment above. The guards rejected an empty subscription result but not a lookup
  that never ran, so the extractor invented the tier. `_parse` now requires the lookup,
  takes `subscription` from the DB record, and rejects a record for a different user.
  Five unit tests (four fail on the old code). 3B: every `ident-*` entry that completes
  passes, `ident-005/013` still fail safe; 8B: now fails safe instead of silently
  downgrading premium users. Behavior change: a model that skips the call stays at the
  greeting. Also found: a runaway 3B generation that hangs `ident-011` on unmodified
  `main` (#30, not fixed).

### Sprint 2 close-out (2026-09-20)

**Definition of done: met.** Retrieval recall@k is 100% and tier leakage 0%, on 39
retrieval entries now against 12 in the Sprint 1 baseline, so neither regressed
(`docs/eval/Precision-FullEval-2026-09-19.md`). Deliverables: KB content corrected
(#6, #16), `scripts/reindex_kb.py`, and a before/after comparison per fix in
`docs/eval/`. Lint is a hard CI gate (#9). Golden set 38 -> 122 entries, 209 unit
tests (Sprint 1: 30).

**The accuracy targets set in the issues were not met.** Each was attacked with the
levers below, measured on held-out entries written before the run, and none reached
target:

| Issue | Metric | Baseline | Now | Target | Tried |
|---|---|---|---|---|---|
| #5 / #17 | Hallucination (hand-graded) | 20% (3/15) | 13.3% fabrication (2/15) on an untuned 15-entry cohort, down from 26.7%; 9.5% (2/21) on the first held-out set | <=5% | stricter answer prompt, KB rewrite, invented-steps guard, larger local model (no gain) |
| #23 | Callback precision (22-entry held-out cohort) | 67% | 83% (2 false triggers in 12), recall 10/10 | >=95% | four alternative wordings (each lost recall), deterministic accept/veto patterns, larger local model (no gain) |

Read these with the caveats in their reports: n is small (one answer is 2-7 points),
the hallucination grade is one reader's judgment, and the latest blind grade of 51
answers (`Model-Experiment-Results-2026-09-20.md`) gives anywhere from 2% to 14%
depending on whether borderline answers count, so the absolute rate is uncertain even
though it is not clearly at target.

**Decision (accepted by the maintainer, Melvin Mathew, 2026-09-20):** stop tuning
these in Sprint 2 and carry them as known limits. The cheap levers are spent: prompt
and KB changes showed diminishing returns, and the larger local model regressed
identification and did not reduce hallucination. What is left is expensive or risky:
more deterministic patterns for #23 would likely overfit a 22-entry cohort, and a
second-pass grounding check for #5/#17 adds a model call per answer for uncertain
gain. If the maintainer wants either pursued, it should be scoped as its own sprint
with a bigger, pre-committed held-out set.

**End-to-end audit and final fixes (2026-09-20, after the close-out merge):** the
maintainer asked for an audit of everything up to this point and for its findings to be
fixed before the sprint was tagged. `docs/eval/Sprint2-Audit-2026-09-20.md` has the
method, findings and before/after live numbers. Nothing regressed; the sprint's claims
held. What changed:
- Docs that contradicted the findings were fixed (the README no longer recommends
  `llama3.1:8b`; the eval README, `Phases.md` Phase 8 and `report.md` were stale).
- **#30 fixed:** every LLM call is bounded (`LLM_MAX_TOKENS`, `LLM_TIMEOUT_SECONDS`), and
  a timeout becomes a reply instead of a crash or a hang.
- **#11 fixed:** the mock lookup ignores email case and matches phone numbers, so the
  greeting's promise is true. `ident-007` and `ident-010` are now scored entries.
- A "no need to call me" phrasing that started a callback is now vetoed; the compound
  case (declines and requests in one sentence) is tracked as #33.
- A silently swallowed exception in the retrieval log now logs a warning.
- Milestones: #5, #17, #23 and #33 moved to an unscheduled `Known limits` milestone
  (they are Sprint 2's unmet targets and a related audit finding, not Sprint 3 work; the
  `Sprint 3` milestone is for session persistence only); Sprint 2 closed and tagged
  `v0.1.0-sprint2`.
- Left open by the maintainer's decision: #14 (license, and whether the Shopify-derived
  KB stays public), which is a legal choice. Later, on `chore/14-license`: the code was
  licensed MIT and `assets/NOTICE.md` records the assets as third-party sample data of
  unconfirmed origin; confirming their source and terms is still open.

**Carried forward (not scheduled in any sprint; the `Known limits` milestone holds #5, #17
and #23, and held #33 until it was fixed on 2026-09-21):**
- #5, #17, #23: open, as known limits (above). #33 (callback veto and compound
  phrasings) was the same family as #23 and was fixed afterwards, with one trade-off
  (`docs/eval/Callback-Compound-Results-2026-09-21.md`).
- Pre-existing: #10 (with-whisper path; exercised on 2026-09-21, found broken, and fixed
  afterwards, see #43 and #44 below), #14 (license
  and whether the Shopify-derived KB stays public). #12 (CLI `EOFError`) and #13
  (chromadb telemetry warnings) were fixed afterwards in a small PR (#36).
- The run-to-run difference (callback recall 100% vs 97% between two full 3B runs on the
  same code) was measured afterwards on `chore/eval-variance`: five full runs gave 0 pp
  spread on every metric and no entry changing result. The earlier difference was one
  model-decided entry (`call-031`), not reproduced and not explained
  (`docs/eval/Variance-Results-2026-09-22.md`). For Sprint 5's gate, that report suggests
  flagging changed entries and re-running only those, instead of a metric threshold.
- `docs/report.md` refreshed for the end of Sprint 2 and again after the audit.

**Deliverables:** updated KB content, `scripts/reindex_kb.py` (or similar),
a before/after retrieval-metrics comparison.
**Definition of done:** retrieval recall@k and tier-leakage rate both
improve or stay at target versus the Sprint 1 baseline — never regress
silently.

---

## Sprint 3 (2 weeks) — Session persistence (Phases.md Phase 6) ✅ Done (merged 2026-09-20, PR #38)
**SDLC stage:** Design → Build
**Goal:** Conversations survive process/session restarts.

**Status (2026-09-20):** built and verified. Design first (`docs/Persistence-Design.md`),
with the four decisions it needed (storage backend, CLI resume behavior, what a finished
conversation does, retention) answered by the maintainer before any code.
- ✅ `SessionStore` (`session_store.py`): SQLite through the standard library, one JSON row
  per conversation, rewritten whole in a transaction; versioned schema with an append-only
  migration list; an unreadable row is a warning and a miss, a newer schema fails loudly.
- ✅ `CustomerSupportPipeline(store=None, session_id=None)` saves after every completed turn
  and resumes by rebuilding the graph and restoring the state (history, current node and its
  typed input, retry counters, conversation id). No store, no change: the eval harness and
  the existing tests are untouched.
- ✅ CLI `--session ID` / `--resume` (nothing resumes implicitly); Streamlit keeps the id in
  the URL (`?session=<id>`). An ended conversation shows its transcript and offers a fresh
  start. `SESSION_DB_PATH` setting; `data/` is gitignored.
- ✅ 60 new tests (244 -> 304, 15 -> 18 files), none needing an LLM. The store and pipeline
  tests were checked by mutation: breaking the counter, id, history or input restore, the
  save, or the resumable-input check each fails a test.
- ✅ **Definition of done, live against `llama3.2:3b`:** the CLI was started, the user
  identified and a question asked, then the process was killed; `--resume` printed the same
  session, replayed the transcript, did not ask to identify again, answered a follow-up from
  the premium KB, and exited 0. The Streamlit app, opened in a fresh process on the same
  URL, redrew the 5 saved messages with no second greeting, highlighted
  `AuthenticatedUserNode` in the Graph tab and answered a follow-up.
- ✅ **Regression check:** a full 122-entry golden-set run on the branch
  (`docs/eval/Sprint3-Persistence-FullEval-2026-09-20.md`, persistence off as in the
  harness) matches the previous full run on every metric (identification 100% n=8,
  fails-safe 100%, recall 100% and leakage 0% on n=39, callback recall 100%, precision 95%,
  held-out cohort 83% with the same two false triggers). Only `ident-007` and `ident-010`
  differ, and only because they are scored PASS now instead of manual review.
- The one edit to an existing test file: the CLI tests (added in #36) pass an empty argv to
  `main()` now that it parses arguments; their expectations are unchanged.
- Found along the way: after identification fails the bot said it could not verify the user
  but kept answering from the free KB (#37). Not fixed in this sprint; fixed afterwards in
  PR #42 (see the out-of-band fixes below). The persistence design refuses to resume such
  a session.
- Not exercised: a real browser session (the app was driven headlessly with Streamlit's
  `AppTest`), and more than one process writing the same database at once (out of scope).
- A process evaluation followed the merge (`docs/Process-Evaluation.md`). Its proposals are
  not adopted; nothing in this file's planning rules changes until the maintainer decides.

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

## Out-of-band fixes after Sprint 3 (2026-09-21)
Not part of any planned sprint - logged here so the history stays accurate. Each was
picked from the open issues, worked on its own `fix/` or `docs/` branch and merged by PR.
- **#37, failed identification (PR #42).** After the identity edge ran out of retries the
  bot said it could not verify the user and then kept answering from the free KB,
  contradicting the PRD. The maintainer chose to end the conversation at that message.
  `AuthenticatedUserNode.is_node_final()` is true whenever the node holds no `UserProfile`,
  so the pipeline reports the conversation over and the CLI and app stop. New golden-set
  entry `ident-014` sends a question after the failure; it failed on the old code and
  passes now. A guard in the pipeline that ignores input after the end was tried and
  dropped as beyond the issue; the eval harness stops sending turns once a conversation is
  over instead, as the real clients do. Behavior change: an unidentified user is no longer
  answered after the fail-safe message.
- **#33, compound callback phrasings (PR #45).** A message that declines one call and
  requests another ("Never call me before 9am, but do call me on ...") was rejected whole
  by the do-not-call veto. Each decline is now taken out of the message before a request
  is looked for. A 12-entry held-out cohort (`call-059`..`070`) was committed first:
  recall on it went 2/7 -> 7/7 and recall over all 44 requests is 44/44. **One trade-off:**
  `call-070` (a decline plus "call me back only if the email bounces", labelled a
  non-request) now false-triggers, so precision on the set fell from 95.1% to 93.6%
  (`docs/eval/Callback-Compound-Results-2026-09-21.md`).
- **#10, the with-audio path exercised (PR #46).** With the `audio` extra installed
  (in a separate short-path venv), Whisper transcribes the sample recording in about 19 s
  and accurately, but the ticket step crashes the callback turn: the 3B returns the ticket
  schema instead of a ticket (**#43**). Installing the extra in a fresh venv also failed on
  `pkg_resources` (**#44**). #10 was closed because its criteria (run it, record it, file
  bugs) were met, not because the path worked. Both bugs were then fixed on
  `fix/43-44-audio-path`: the ticket is asked for with structured output and a parse
  failure falls back to the "callback logged" reply (#43), and the extra pins
  `openai-whisper==20250625`, which builds in a fresh venv (#44).
- Still open and unscheduled: #5, #17 and #23 (accepted known limits; no attempt was made
  to reach their targets, since the samples are too small to confirm a fix, see
  `docs/Process-Evaluation.md`) and the open part of #14 (confirm the source and terms of the assets, a maintainer decision).

---

## Sprint 4 (2 weeks) — Real user store (Phases.md Phase 7) ✅ Done (branch `sprint-4`)
**SDLC stage:** Build + integration testing
**Goal:** Replace the mock DB without touching conversation logic.

**Status (2026-09-22):** design first (`docs/User-Store-Design.md`), with the two
decisions it needed (storage backend, whether to add a second identification factor)
answered by the maintainer before any code — this project has no real storefront system
behind it, so "real lookup" meant deciding what "real" should mean here, not integrating
an actual external API.

- ✅ **`tools/user_store.py`**: a `UserStore` `Protocol` (`search_user_info`,
  `search_user_subscription` — the interface the two existing tool functions already
  implied), `MockUserStore` (today's in-memory fixture data, unchanged), and
  `SqliteUserStore` (stdlib `sqlite3`, auto-seeds the same fixture into a real database the
  first time it opens an empty one — no separate seed script to run or forget, matching
  `SessionStore`'s self-healing-on-open posture). Both stores read one canonical copy of
  the fixture data and share the same matching helper, so mock and real cannot silently
  drift apart. Matching stays in Python rather than SQL: the table is a handful of rows, so
  there is one place to get the matching rule right, not two.
- ✅ **Contract tests** (`tests/tools/test_user_store.py`, 34 tests): today's user-lookup
  cases, parametrized over both stores — a behavior difference between them fails a test
  instead of shipping.
- ✅ **Wired in**: `Settings.user_store_provider` (`mock`/`sqlite`, default `sqlite`) and
  `get_user_store()` mirror the existing `llm_provider`/`get_chat_model()` pattern.
  `UserInfoChainBasedEdge(user_store=...)` defaults to `MockUserStore()`, so every existing
  call site and all 335 prior tests were unaffected until `pipeline.py` was changed to pass
  the configured store — the one commit that actually changed production wiring.
  `tools/user_info_db.py` and its test file, now dead code, were removed; their assertions
  already live in the new contract tests, plus one concurrency test added during the
  end-to-end audit (below). 354/354 tests pass (370 minus the 16 retired
  duplicate cases), ruff clean.
- ✅ **Regression verified**: a fast 14-entry identification-only subset run
  (`--ids ident-*`) against the new sqlite-backed default matched the baseline exactly
  (identification success 100% n=8, fails-safe 100% n=6) before committing to the full
  135-entry run. The full run: `docs/eval/Sprint4-UserStore-FullEval-2026-09-22.md`,
  diffed against `docs/eval/variance/run-5.md` (the latest full run on unchanged `main`)
  with `scripts/summarize_eval_runs.py` — see the result recorded there and in
  `docs/report.md`.
- Not built: a manual seed script (auto-seed made it unnecessary) and a second
  identification factor (decided against for this sprint, `docs/User-Store-Design.md`
  decision 2).

**End-to-end audit (2026-09-22, before merge), mirroring Sprint 2's own audit-before-tag
practice.** A manual pass plus a backgrounded automated code review over the full
`main..sprint-4` diff found and fixed five things - three from the manual pass, two more
(hermeticity, connection closing) from the automated review - none of which changed any
LLM-facing behavior (the golden-set regression in §10.8 was run before these fixes; they
were re-verified with the full unit suite and a live CLI check instead of a second full
run, since none of them touch anything LLM-facing):
- **A real race in the auto-seed.** `SqliteUserStore` seeded with a `SELECT COUNT(*) == 0`
  check followed by `INSERT`. Two stores opening the same brand-new file at once (e.g. two
  Streamlit sessions on a fresh install) could both see zero rows and both try to insert,
  crashing the second on the `user_id` primary key. Confirmed real, not hypothetical: a
  forced-interleaving reproduction raised `IntegrityError` on the old code. Fixed with
  `INSERT OR IGNORE`, which is correct regardless of timing since there's no check-then-act
  step left to race; a concurrency test (8 threads racing to open the same file) guards it
  going forward.
- **A shared-mutable-fixture footgun.** `MockUserStore` held direct references to the
  module-level `USERS`/`SUBSCRIPTIONS` lists rather than copies. Nothing writes through a
  store today, so this wasn't yet exploitable, but a future write would have silently
  corrupted the fixture for every other instance. Fixed with a defensive copy in
  `__init__`.
- **Style inconsistency.** The new module used lowercase generic type hints (`list[dict]`)
  and `UserInfoChainBasedEdge.__init__` took `*args, **kwargs`; both diverge from this
  codebase's established explicit-signature, `typing.List`/`Dict` style (`session_store.py`
  is the closest precedent). Both were made explicit to match.
- **Broken test hermeticity, caught by an automated review pass.** `get_user_store()` was
  resolved eagerly in `CustomerSupportPipeline.__init__`, so every bare
  `CustomerSupportPipeline()` - including in tests that monkeypatch `_get_pipeline` away
  entirely (`fake_graph` in `tests/test_pipeline_persistence.py`, used by 22+ tests) - wrote
  a real `data/users.sqlite` on every test run. One test's own assertion
  (`test_without_a_store_nothing_is_saved_and_there_is_no_session`) claims no disk I/O
  happens with no store configured, and still passed, because it only checks `tmp_path`,
  not where the user store actually writes - the test's name was no longer true. Fixed by
  moving the resolution into `_get_pipeline()` itself, where the design doc said it
  belonged from the start; tests that fake that method out now never touch the real store,
  the same way they never touch a real LLM.
- **Connections never explicitly closed.** `SqliteUserStore` used `with self._connect() as
  conn:` throughout, but a bare `with conn:` on a `sqlite3.Connection` only manages the
  transaction (commit/rollback) - it does not close the connection, unlike
  `session_store.py`'s `SessionStore`, which wraps every connection in `contextlib.closing`.
  Fixed to match that convention (`closing(self._connect())`, paired with `conn` itself for
  the one write path); also added the same explicit `timeout=5` `SessionStore` already
  passes (matches Python's own default, but makes it visible rather than implicit).

**Deliverables:** real user-store adapter, contract tests.
**Definition of done:** met — swapping `USER_STORE_PROVIDER=mock` to `sqlite` (now the
default) is a config change, not a code change in `agents/`; identification metrics did
not regress.

---

## Sprint 5 (2 weeks) — Automated evaluation harness & regression gate (Phases.md Phase 8) ✅ Done (PR #52, hotfix #55)
**SDLC stage:** Test automation / CI
**Goal:** Turn Sprint 1's manual eval into a repeatable, CI-enforced gate.

**Status (2026-09-22):** design first (`docs/Eval-Gate-Design.md`), with the backend
decision (GitHub-hosted runner, install+cache Ollama, gate on a curated subset - not a
self-hosted runner, which GitHub warns against for public repos, and not a live-model-free
gate, which wouldn't satisfy this sprint's own Definition of Done) answered by the
maintainer before any code.

- ✅ **`scripts/eval_gate.py`**: runs 14 hand-picked golden-set entries (one or two per
  category, weighted toward tier-leakage and callback - the two historically most fragile
  areas) and fails if any entry that wasn't failing starts failing, against a checked-in
  `tests/eval/ci_baseline.json`. Aggregate metrics are computed and printed for context but
  are deliberately not a second, independent gate - they're derived from the same 14
  results the entry check already looked at individually, so a metric-floor check would
  only restate a regression already caught. 10 unit tests on the comparison logic, no live
  model needed.
- ✅ **Wired into CI**: a new `eval-gate` job in `ci.yml`, separate from the existing `test`
  job so the fast unit-test/lint signal never waits on a live model. PR-only. Installs
  Ollama, stops its auto-started systemd service so the server it starts itself (with
  `OLLAMA_MODELS` pinned) is the only one listening, caches the two model blobs via
  `actions/cache`, runs the gate. Confirmed against real GitHub Actions, not just locally:
  first run (cold cache) took 13m13s; the install/cache/systemd handling worked exactly as
  designed.
- ✅ **Definition of done, proven for real**: a disposable branch/PR deliberately broke
  `_get_retriever` to always return the paid KB regardless of tier. The `eval-gate` job
  **did fail** on it (`rag-adv-001`/`rag-adv-002`, tier leak), exactly as designed - the
  gate mechanism itself works.
- 🐛 **Found by this sprint's own proof, the hard way.** The disposable proof PR (labelled
  "TEST - DO NOT MERGE" in its title, body, and the code comment itself) was merged into
  `main` anyway, alongside the real Sprint 5 PR - because `eval-gate` was not yet
  configured as a *required* status check in GitHub's branch protection settings, a PR can
  merge regardless of what CI reports. For a few minutes, `main` served every user the
  paid knowledge base regardless of their actual tier. Caught immediately (the merge
  history was checked directly, not assumed from a status message), fixed with a `git
  revert -m 1` of the one bad merge commit (hotfix PR #55, verified green - `eval-gate`
  passing on the revert, unit suite passing except one confirmed-unrelated pre-existing
  flake) and merged. **This is exactly the gap `docs/Eval-Gate-Design.md` and
  `Git-Workflow.md` already flagged** ("has to be added as a required check under branch
  protection to actually block a merge instead of just reporting red") - it just hadn't
  happened yet, and this incident is the concrete reason to do it now, not a hypothetical.
- Not built: per-metric numeric thresholds (rejected in the design - redundant with the
  entry-level check on a fixed subset, see `Eval-Gate-Design.md`); the full 135-entry set
  in CI (stays a manual pre-merge step, per the existing PR template checklist).

**Closed the same day (2026-09-22):** `eval-gate` and `test` are now both configured as
required status checks under GitHub's branch protection for `main` (via the API, every
other existing protection setting - `enforce_admins`, force-push/deletion blocks, the PR
requirement - preserved exactly, not reset). A GitHub Settings change, not something a
commit alone could do - see `docs/Git-Workflow.md`'s recommended settings, now current
rather than aspirational.

**Deliverables:** CI eval job, `docs/Eval-Gate-Design.md`, `Git-Workflow.md` updated.
**Definition of done:** met - deliberately regressing the free/paid retriever selection
made the `eval-gate` CI check fail, watched live on GitHub Actions, not simulated.

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
  changelog line) and re-verified against the repository (the report is
  also updated in each PR that changes what it states, per the PR
  template), and — from Sprint 5 onward — the CI eval gate is green.
- Sprints are sequential as scoped above (each depends on the eval
  foundation from Sprint 1), but Sprints 3/4 (persistence, user store) and
  Sprint 6 (design) don't depend on each other and can be reordered or
  parallelized if more than one person is working on this.
