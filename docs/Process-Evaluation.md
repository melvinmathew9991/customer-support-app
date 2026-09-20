# Process evaluation and improvement plan (2026-09-20)

An evaluation of how this project has been built, from the point of view of an
experienced data scientist, written at the end of Sprint 3. It is about the **process**, not
the product: how work is planned, measured, verified, reviewed, documented and released.

**Basis.** The repository's own record, measured on 2026-09-20 before this document was added:
82 commits on `main` over three days (4, 47 and 31 commits on the three days), 20 merged pull
requests, 20 issues, 36 CI runs, 35 files in `docs/eval`, and the docs. Nothing outside the repo was
seen: no conversations, no users, no record of how the time was spent.

**Status of the proposals.** Everything under "Improvement plan" is a **proposal**. None of it
is adopted, and nothing in `Sprints.md`, `Rules.md` or `Git-Workflow.md` has changed to reflect
it. Adopting any of it is the maintainer's decision.

## Bottom line

The process is unusually disciplined for an LLM project: it is measurement-first, it
pre-registers its held-out tests, and it reports misses honestly. Its weak spots are
statistical power, independence of review, reproducibility of the eval runs, and documentation
that duplicates itself. The main risk is trusting numbers that look precise but cannot carry
the conclusions drawn from them.

## Scorecard

| Dimension | Rating | One-line reason |
|---|---|---|
| Sequencing and strategy | 4.5 / 5 | Evaluation was built before features; the deterministic-versus-LLM boundary is explicit |
| Experiment discipline | 4 / 5 | Held-out sets and decision rules committed before runs; caught its own optimism |
| Statistical rigor | 2 / 5 | Targets cannot be tested at the sample sizes used |
| Reproducibility and tracking | 2 / 5 | No run manifest, no tracker, single runs |
| Testing | 4 / 5 | Strong deterministic tests, mutation-checked; no automated LLM regression gate yet |
| Engineering hygiene | 4 / 5 | CI, protected `main`, tags, explanatory commits |
| Independent review | 1 / 5 | 20 pull requests, 0 reviews, 0 comments |
| Documentation | 3 / 5 | Accurate after the audit, but heavy and duplicated |
| Planning and project management | 2.5 / 5 | "Two-week" sprints ran in about three days |
| Risk (privacy, legal, security) | 2.5 / 5 | PII stored in the clear, no license, little adversarial testing |
| Product validation | 1.5 / 5 | No real users; targets not derived from the cost of errors |

## What is strong

- **Order of work.** Sprint 1 built the golden set, the metrics with targets and the harness
  before any feature work, so everything after it was measurable.
- **Pre-registration.** Held-out cohorts, and the larger-model experiment's criteria and
  decision rule, were committed before running. This exposed real optimism: hallucination read
  6.7% on the tuned set but 9.5% held-out, and callback precision read 100% but 83%.
- **Triage before fixing.** The model was found to ignore retrieved context (a generation
  problem) before the retriever was touched.
- **A stop rule.** The cheap levers were spent, diminishing returns were measured, and the
  remaining limits were accepted explicitly and parked in a `Known limits` milestone.
- **Deterministic guards.** Identity, tier choice and the callback digit check are not left to
  the model, which is the right principle for this product.
- **Traceability.** Commit bodies explain why; PRs list behavior changes; CI was green on all
  36 runs; branch protection requires a PR and the `test` check.
- **Self-audit.** The Sprint 2 audit found real defects, such as a README advising the
  model the experiment had rejected.

## Weaknesses, with evidence

**1. Statistical power is the largest gap.** 95% Wilson intervals, computed for the rates the
project reports:

| Reported | 95% interval |
|---|---|
| Callback precision on held-out negatives, 10 of 12 (83%) | 55% to 95% |
| Callback precision, full set, 37 of 39 (94.9%) | 83% to 99% |
| Hallucination, 2 of 15 (13%) | 4% to 38% |
| Hallucination, 2 of 21 (9.5%) | 3% to 29% |
| Blind grade, 1 of 51 (2%) | 0.3% to 10% |
| Blind grade counting borderline answers, 7 of 51 (14%) | 7% to 26% |

Showing an error rate of 5% or less needs about 60 cases with zero failures (the rule of
three). Even a perfect 12 of 12 only bounds precision at 76% or better, so the held-out cohort
could not have confirmed a 95% target. The 2% and 14% readings of the same answers sit on
opposite sides of the 5% target with overlapping intervals. Most decisions were made on
differences smaller than the noise. The report says n is small; the gap is that targets were
set without a power calculation.

**2. The golden set gets used up.** The same 122 entries fed about 15 full runs, and the
22-entry callback cohort was reused across several wordings and pattern changes, after which it
was no longer held out. Entries, fixes and grading came from one author, so distribution shift
is untested. Hallucination is graded by one reader, the latest blind pass by the same assistant
that ran the experiment, with no written rubric or second grader.

**3. Some metrics cannot fail.**
- Retrieval recall@4 on an index of 14 to 15 chunks retrieves 27% to 29% of the corpus, so 100%
  says little about retrieval quality.
- Sprint 1's callback precision was 100% because its negatives contained no digits. It was
  caught, but only after being reported.
- Targets such as "5% or less hallucination" and "95% or better precision" are round numbers,
  not derived from costs (a false callback wastes an agent's time; a missed one frustrates a
  customer).

**4. Runs are not reproducible from the artifacts.** The eval reports carry no git SHA, model
digest, temperature or timestamp header. Thirty-five markdown files in `docs/eval` hold about 19,700 lines of
raw run output instead of structured results. Temperature 0 still varied between runs (callback
recall 97% versus 100% on the same code), and single runs cannot separate that variance from a
real change.

**5. Modeling strategy had some whack-a-mole.** The callback work moved from prompt wording to
regexes to more regexes, each flattering the entries it was written for, and the audit found two
phrasings they got wrong (one since fixed, one still open as #33). The alternative was not tried: a labeled intent set of 150 to 200
examples evaluated against a small classifier. "A larger model did not help" is really "one
4-bit 8B model, with prompts tuned for the 3B, did not help"; no hosted-model baseline was run
although the OpenAI path is wired.

**6. LLM regressions are caught manually.** CI runs only deterministic tests, the live eval is
manual, and the automated gate is planned for Sprint 5. Sprints 2 and 3 changed prompts,
patterns and the pipeline without one.

**7. No independent review.** All 20 pull requests have zero reviews and zero comments. Branch
protection requires a PR and green CI but no reviewer, so the same author and assistant wrote
the code, the tests, the eval labels and the grades; correlated mistakes go unseen. PRs are hard
to review: the median is about 890 added lines and 5 of 20 exceed 3,000, mostly eval dumps.

**8. Documentation costs more than it returns.** Docs plus eval reports were about 9.2 times the
size of the source (21,400 lines against 2,337). The same facts live in `report.md`,
`Sprints.md`, `Phases.md`, PR bodies, commit bodies and eval reports, and drift followed: the
audit found stale counts and contradicted advice. Counts in prose are typed by hand.

**9. The planning unit does not match reality.** Sprints ran in about three days, with 47 commits
on the busiest. They work as milestones but not as capacity planning; Sprints 4 to 7 are still
scheduled at two weeks each with no estimates.

**10. Risk and product validation are thin.** Saved sessions hold PII in plaintext and the
Streamlit URL id acts as a bearer token. `logs/turns.jsonl` stores raw `user_input`, including
emails and phone numbers. The repository has been public without a license since the start
(#14). There is no dependency lockfile, and an unpinned transitive dependency (`posthog`)
already broke chromadb's telemetry. Adversarial testing is 11 entries and nothing covers prompt
injection. There are no real users, and the KB is four files per tier, so results will not
generalize to a production store.

**11. AI-assisted development has its own risk.** Volume is high and confident, and errors read
as fact. The audit step was the right mitigation and worked; it should be routine, with
independent grading added.

## Improvement plan (proposed)

Ordered by payoff per effort. The codebase is small, so the aim is fewer things trusted more,
not more ceremony.

### 1. Make the numbers trustworthy
- **Split the data by role.** Dev (tune against it; anything that informed a change stays dev
  for good), validation (choose between options), and a frozen test set run once per milestone
  and never tuned against. Write frozen-test entries in a different session, or have someone
  else write them, before the code they test.
- **Size sets from the target.** Add a "testable?" table to `Metrics.md`: target, cases needed,
  cases now, status. Rule of thumb: about 60 cases with zero failures to show 5% or better, and
  about 100 to estimate a rate within 10 points. Below that a metric is labelled directional and
  cannot be reported as target met or missed.
- **Report intervals and compare properly.** Wilson 95% intervals on every rate; compare two
  versions item by item (McNemar), not two raw percentages; run the baseline three times first to
  measure run-to-run noise and ignore improvements smaller than it.
- **Grade with a protocol.** A short rubric (supported, unsupported but harmless, fabricated,
  contradicted); two graders blind to the version (a human plus a judge model, say); Cohen's
  kappa for agreement; disagreements settled by hand. Grading stays with a human.
- **Derive targets from costs.** Write down what a false trigger and a missed request cost, and
  set precision and recall from that.

### 2. Make every run reproducible and searchable
- Each eval writes `manifest.json`: git SHA and dirty flag, model name and digest, embedding
  model, temperature and settings, golden-set hash, timestamp, duration.
- Layout `results/<run_id>/{manifest.json, results.jsonl, summary.md}`, with raw dumps kept out
  of git (CI artifacts or a gitignored folder) and one small committed `results/index.csv` with
  a row per run.
- A `compare_runs.py A B` script prints the differences with intervals. A tracker such as
  MLflow is optional; a CSV index is enough for one person. This also shrinks PRs.

### 3. Catch LLM regressions automatically
- Every PR: deterministic tests (exists). Before merge: a smoke eval of about 30 entries
  (identification, fails-safe, tier leakage, a callback sample; roughly three minutes) with hard
  thresholds, run through a pre-push hook. Weekly: the full set, recorded in the index.
- CI runners have no Ollama, so the cheapest enforcement is a CI check that the PR includes a run
  manifest whose SHA matches the head commit. Recorded model responses, or a self-hosted runner,
  are heavier options. Do this before Sprint 5.

### 4. Get real review
- Add at least one independent human for the eval labels and for any PR that changes a metric.
  Until there is a collaborator: a self-review checklist plus a 24-hour wait on metric-affecting
  merges. A fresh assistant session with a different prompt is a useful extra reviewer, not a
  replacement.
- Keep PRs to about 400 code lines by moving data artifacts out; one behavior change per PR with
  its eval delta in the body.

### 5. Cut documentation to what can be trusted
- One source per fact: metrics live in the results index and counts come from code; prose links
  instead of copying.
- A generated status block (test count, line counts, open issues, latest metrics) embedded in
  `report.md`.
- A short decision log, `docs/decisions/NNN-title.md` (context, choice, alternatives,
  consequences), replacing decisions scattered across narrative documents.

### 6. Plan with real numbers
- Re-baseline: one-week or "session" timeboxes; measure throughput for two or three cycles
  before committing to a scope. Write goals as outcomes ("free-tier questions at 95% or better on
  a frozen 60-entry set"), add spike timeboxes and a work-in-progress limit of 1 or 2, and end
  each sprint with keep, stop, start and one dated action.
- Re-check Sprints 4 to 7 for value: the eval gate (Sprint 5) and a small real-user trial
  arguably belong before a real user store.

### 7. Manage risk on purpose
- A one-page threat model: plaintext PII at rest, the URL id as a password, raw `user_input` in
  the turn log (add a redaction option), prompt injection (a 20 to 30 entry test set), tier
  bypass, and the failed-identification behavior (#37).
- A dependency lockfile plus Dependabot, a secrets scan in CI, and a decision on the license
  (#14).

### 8. Validate with people
Have 3 to 5 people, ideally with support experience, try it for 15 minutes each and record where
it fails; save about 50 real messages as a seed "real traffic" set; add a thumbs up or down; and
define one north-star metric, such as conversations resolved without a human.

### 9. Baselines before building
Before writing rules, measure a trivial baseline, the strongest available model (the OpenAI path
is wired and unused) and a simple classical option. For callbacks that means a labeled intent
set and a small classifier. Track p50 and p95 latency and token use per turn; the turn log can
already give latency.

### 10. Guardrails for AI-assisted work
Every number in a doc links to a run id; the end-of-sprint audit becomes routine, run from a
checklist; labels, grading and decisions stay with a human; the assistant that wrote a change is
not the only one to check it.

## Stop doing

- Committing raw run dumps.
- Hand-typing counts into prose.
- Calling three-day blocks two-week sprints.
- Treating a cohort that was tuned on as held-out.

## Would-be process metrics

If the plan is adopted, track these each sprint: the share of metrics with enough cases to be
testable; the share of runs with a manifest (target 100%); measured run-to-run noise on a
repeated baseline; median PR size and the number over 1,000 lines; stale facts found per audit
(target 0); and defects found by the audit rather than by tests.

## Suggested first step

One pull request with the evidence bundle (sections 1 and 2: splits, interval reporting, run
manifests, the compare script and a generated status block). Everything else reports through it.
Grading rules and the frozen test set need a human author and are not part of it.

## Limits of this evaluation

It rests only on what the repository shows. Ratings are one reviewer's judgment, not a
measurement. The interval calculations are exact for the counts given, but the counts come from
single runs on one 3B model, so they describe what was observed, not the model's true rates.
