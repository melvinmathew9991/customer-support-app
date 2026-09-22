# CI evaluation regression gate — design (Sprint 5, Phases.md Phase 8)

**Status:** locked backend decision - GitHub-hosted runner, install and cache Ollama, gate
on a curated smoke subset (maintainer, 2026-09-22). Self-hosted runner rejected: this repo
is public, and GitHub explicitly warns against self-hosted runners on public repos (a
`pull_request` from anyone can execute code on the runner via the workflow already on
`main`). A live-model-free gate was also rejected: it would satisfy repeatability but not
Sprint 5's own Definition of Done ("regressing tier-leakage fails CI"), which needs
something in GitHub Actions to actually block a PR.

**Goal (Sprints.md):** a PR that regresses identification, retrieval, tier-leakage or
callback behavior fails CI automatically - proven, not just plausible, by deliberately
breaking something on a scratch branch and watching the gate catch it.

## Why a subset, not the full 135

The full golden-set run takes 13-14 minutes on the maintainer's own machine
(`docs/report.md` §10.7) against a local Ollama server. GitHub-hosted `ubuntu-latest` is
CPU-only, shared, and starts every job from a clean disk - even with the model blob
cached, per-entry inference will be slower than local, and paying that cost 135 times on
every PR would make CI slow enough that people stop trusting or waiting for it. The
existing PR template already requires a full run as a **manual** step before merging
anything that touches LLM-facing code; that doesn't change. CI adds a fast, automatic
floor under it: a small subset, run on every PR, catching the loud, obvious regressions
(a node that no longer transitions correctly, a tier that leaks) without claiming to
replace the full run's coverage.

## Smoke subset

One or two entries per golden-set category (14 entries, all 11 categories represented),
weighted toward the two historically most fragile areas - tier-leakage and callback
detection:

| Category | Entries | Why these |
|---|---|---|
| `happy_path_identification` | `ident-001` | Baseline identify-by-email path |
| `ambiguous_identification` | `ident-003` | Has a fixed expected identity to score against (some entries in this category don't - see `score_identification`) |
| `unknown_user_identification` | `ident-004` | Fails-safe path |
| `subscription_lookup_missing` | `ident-005` | The other fails-safe path (#29's guard) |
| `free_tier_question` | `rag-free-001` | Retrieval, free tier |
| `paid_tier_question` | `rag-paid-001` | Retrieval, paid tier |
| `adversarial_tier_crossing` | `rag-adv-001`, `rag-adv-002` | **Tier-leakage** - two entries, since this is the sprint's own literal DoD example |
| `out_of_scope_question` | `rag-oos-001` | Callback false-trigger check (see below - this category can still fail even though hallucination itself is graded manually) |
| `callback_request_explicit` | `call-001`, `call-004` | Callback recall |
| `callback_request_indirect` | `call-002` | Callback recall, indirect phrasing |
| `callback_false_trigger` | `call-003`, `call-009` | Callback precision |

Every entry here scores a real `True`/`False` verdict from `tests/eval/run_eval.py`'s
existing scorers **except** `rag-oos-001`: `score_out_of_scope` returns `False` if the
conversation falsely reaches `CallCustomerNode` (a real, auto-gradable failure) and `None`
otherwise (hallucination grading is manual, per `docs/eval/Metrics.md` #5 - the gate
never touches that). No entry here was chosen from the project's known current failures
(`call-042`, `call-047`, `call-070`) - the gate's job is to catch new regressions, not
re-litigate accepted known limits (#5, #17, #23) on every single PR.

## Gate mechanism (`scripts/eval_gate.py`)

Imports `load_golden_set`, `run_all`, `compute_metrics` directly from
`tests/eval/run_eval.py` - already plain Python functions with no file/subprocess
dependency, so no markdown parsing is needed (unlike `scripts/summarize_eval_runs.py`,
which parses dated human-readable reports for a different purpose).

**The only hard-fail check is per-entry: did anything that wasn't failing start
failing?**

```
flag r if baseline[r.id] is not False and current[r.id] is False
```

This one rule covers every case that matters:
- `True -> False`: a previously-passing entry now fails - the obvious case.
- `None -> False`: `rag-oos-001` used to stay silent (or get manually reviewed) and now
  falsely triggers a callback - also a real regression, and the only way
  `out_of_scope_question` can regress in an auto-gradable way.
- `False -> False`: already broken, not a new regression - never re-flagged (this is
  what keeps the gate from permanently failing CI over #5/#17/#23's accepted misses,
  since none of those entries are in the smoke subset anyway, but the rule holds even if
  a future subset change included one).

**Aggregate metrics (`compute_metrics`) are computed and printed for context, not used
as a second, independent pass/fail trigger.** They're derived entirely from the same 14
results the entry check already looked at individually, so a metric-floor check here
would only ever restate a regression the entry check already caught - not add new
detection power, just a second, more confusing way to report the same root cause.

**Manifest.** Every gate run (and every `--update-baseline`) stamps the git SHA, the
configured model, and a timestamp into `tests/eval/ci_baseline.json`, closing
`docs/report.md`'s own finding #28 ("eval runs carry no manifest") - directly relevant
now that a report is a CI baseline something needs to be traceable to.

**Baseline file (`tests/eval/ci_baseline.json`).** Checked into git, like the golden set
itself. Regenerated deliberately with `--update-baseline` when a change legitimately
shifts expected behavior - never auto-updated by the gate on a pass, the same way
held-out eval entries are committed as reviewed state, not silently rewritten.

## CI wiring

A **new, separate** job in `.github/workflows/ci.yml`, not folded into the existing
`test` job - so lint/unit-test feedback (fast, no model dependency) and the smoke gate
(slower, needs Ollama) report independently and in parallel, and a smoke-gate failure
never hides behind a slow job. Runs on `pull_request` only: `main` is already gated at
PR time, so re-running after merge adds nothing. Ollama is installed fresh each run
(official install script); the two model blobs (`llama3.2:3b`, `nomic-embed-text`) are
cached via `actions/cache` keyed on model name, so an unchanged model isn't re-downloaded
on every PR - only the first run (or a cache eviction) pays that cost.

## Out of scope

Running the full 135-entry set in CI (stays a manual pre-merge step). Hallucination
grading in CI (stays manual, per `docs/eval/Metrics.md` #5 - it needs a human reader).
Gating on the aspirational `docs/eval/Metrics.md` targets rather than today's baseline
(would fail CI forever on #5/#17/#23's already-accepted misses). A self-hosted runner
(rejected above). Flakiness retry/quarantine logic for the one known intermittently
flaky entry, `call-031` (`docs/report.md` §10.7) - not in the smoke subset, so not yet a
live concern; revisit if a chosen smoke entry turns out to flip on its own.

## Tests

- **Gate comparison logic** (`tests/eval/test_eval_gate.py`, sibling to
  `test_run_eval_scoring.py`): fabricated `results`/`baseline` dicts, no live model -
  `True->False` flags, `None->False` flags, `False->False` does not, an id missing from
  the golden set entirely is a hard error (not a silent skip), a clean run against itself
  flags nothing.
- **Live check (this sprint's actual Definition of Done):** `--update-baseline` run once
  against the real pipeline to seed `ci_baseline.json`; then, once wired into CI, a
  deliberate regression on a scratch branch/PR must make the gate job fail, watched live
  on GitHub Actions - not simulated locally, since the CI environment (fresh Ollama
  install, CPU-only inference, `actions/cache`) can't be fully reproduced on the
  maintainer's machine.
