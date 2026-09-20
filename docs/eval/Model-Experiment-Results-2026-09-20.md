# Larger local model experiment: results (Sprint 2, #5, #17, #23)

Plan and criteria: `Model-Experiment-Plan-2026-09-19.md` (committed before any run).
Raw runs: `Model-Full-llama3-2-3b-2026-09-19.md`, `Model-Full-llama3-1-8b-2026-09-19.md`
(full 122-entry golden set, one run each, temperature 0, same code and KB).

## Verdict

**Not sufficient. The decision rule is failed on all three conditions, with the 8B as
the pipeline is written today.** The 8B does not reduce hallucination on this set, it
lowers callback recall, and it breaks identification (and everything downstream of
it) because it does not make the second tool call. Whether to move the default off a
small local model remains the maintainer's decision.

| Condition | Required | 3B | 8B | Met by 8B |
|---|---|---|---|---|
| Callback precision / recall, held-out `call-037`..`058` | >=95% / >=90% | 83% (10/12) / 100% (10/10) | 100% (8/8) / 80% (8/10) | No (recall) |
| Hallucinated answers (51 answered `rag-*`) | >=3 fewer than 3B | 1 | 1 | No (0 fewer) |
| No regression | all hold | all hold | identification 50%, fails-safe 60%, retrieval recall 62%, tier leakage 38% | No |

## Machine-scored metrics (full golden set)

| Metric | Target | 3B | 8B |
|---|---|---|---|
| Identification | >=95% / >=80% ambiguous | 100% | 50% |
| Fails-safe | 100% | 100% | 60% |
| Retrieval recall@k | >=90% | 100% | 62% |
| Tier leakage | 0% | 0% | 38% |
| Callback recall | >=90% | 100% | 81% |
| Callback precision | >=95% | 95% | 100% |
| Phone extraction | none | 100% | 100% |
| Callback false-trigger rate | none | 6% | 0% |

## Why the 8B regresses: one mechanism

Diagnosed by running `UserInfoChainBasedEdge` directly and then through the eval
pipeline (`run_conversation`), 3 repeats each, all consistent.

- `llama3.1:8b` makes the first tool call (`user_info_db_search`) correctly, then
  writes the second one as **plain text** in its reply
  (`{"name": "user_subscription_db_search", "parameters": {"__arg1": "3"}}`) instead of
  a structured tool call. The subscription tool never runs.
- `UserInfoChainBasedEdge._parse` only rejects an **empty** subscription result
  (`_NO_SUBSCRIPTION_MATCH`). It does not check that the tool was called at all, so the
  structured extractor is asked to fill `subscription` from findings that contain none.
  It returns `"free"` (ident-002, and every premium login through the pipeline) or the
  literal string `user_subscription_db_search result` (ident-006 in isolation).
- `AuthenticatedUserNode` then serves the free KB to premium users. That accounts for
  the tier leakage and retrieval collapse: all 14 `rag-paid-*` entries log in as
  Michael Jackson or Carl Sagan. It also accounts for fails-safe dropping to 60%:
  `ident-005/013` (no subscription record) reach `AuthenticatedUserNode` instead of
  failing safe.
- Reproduced with the realistic history (the greeting message present). Without the
  greeting in the history, `ident-002` passed 3/3 in isolation but failed 3/3 through
  the pipeline, so the history matters.

This is a property of the model and stack together, and the missing guard is a gap in
the code that would also bite any model that skips the call. It is out of scope for a
model-only experiment, so the pipeline was not changed. Requiring the subscription
tool call in `_parse` would make the 8B fail safe instead of silently downgrading
users, but would not make it identify them; that needs its own issue.

## Callback, held-out cohort (12 negatives, 10 positives), full pipeline

| | 3B | 8B |
|---|---|---|
| False triggers | 2 (`call-042`, `call-047`) | 0 |
| Missed requests | 0 | 2 (`call-054`, `call-057`) |
| Precision / recall | 83% / 100% | 100% / 80% |

Model-only intent check (deterministic patterns bypassed, greeting-only history),
same 22 messages:

| Model | Wording | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|
| 3B | previous | 10 | 10 | 0 | 50% | 100% |
| 3B | current | 7 | 1 | 3 | 88% | 70% |
| 8B | previous | 0 | 0 | 10 | n/a | 0% |
| 8B | current | 0 | 0 | 10 | n/a | 0% |

The 8B answered "no" to all 22 messages under both wordings. This is a real answer,
not an error swallowed by `check()`: a direct call returned `Validation(is_valid=False)`
for "Ring me: 0452 349 771". So its 100% precision is not judgment; the model never
says yes. Its 80% pipeline recall comes from the deterministic `_CALL_ME_RE`, and the
two misses are exactly the two positives whose wording the patterns do not catch
("speak to someone on the phone", "contact me by phone"), which fall through to the
model.

## Hallucination, hand-graded, blind

51 answered `rag-*` entries, 85 distinct answers (17 identical across models get one
verdict). Shuffled, model labels withheld, key kept in a separate file and opened only
after grading. Rubric as in `Hallucination-Grading-2026-09-19.md` (hallucinated =
asserts something the KB does not support or contradicts it, or answers confidently
when the KB does not cover it). **B** = borderline judgment call, not counted in the
headline. **R** = refused with "I don't have information", not a hallucination.

| | 3B | 8B |
|---|---|---|
| Hallucinated (H) | 1 (2%) | 1 (2%) |
| Borderline (B) | 6 | 1 |
| Refused (R) | 11 | 20 |
| Supported | 33 | 29 |
| H + B (upper bound) | 7 (14%) | 2 (4%) |
| Held-out 21 only | 0 H, 2 B, 5 R | 1 H, 0 B, 10 R |

Difference in clear hallucinations: **0** (needed 3). The upper bound shows 5 fewer for
the 8B, but the 8B also refuses 9 more questions, and 10 of its 20 refusals are
premium-login users answered from the free KB that lacks the answer. So the gap is
mostly abstention caused by the identity failure, not better grounding.

Graded items:

| Entry | Model | Grade | Reason |
|---|---|---|---|
| `rag-oos-011` (connect a card reader) | 3B | H | Invented setup steps; no KB text covers it. |
| `rag-free-008` (copyright vs trademark) | 8B | H | Gives trade-dress wording (size, shape, colour) as what a trademark protects; the KB separates them. |
| `rag-oos-009` (enable Shopify Payments) | both | B | "Payment providers area" is in the KB but not as setup steps. |
| `rag-adv-007` | 3B | B | Right conclusion, invented reasoning ("two cities implies in-person selling"). |
| `rag-adv-010`, `rag-adv-006` | 3B | B | "No" to COD / email transfer inferred from the general manual-payments rule on the free KB. |
| `rag-free-012` | 3B | B | Adds "in your store admin" to the copyright form; the KB says that only for counter notices. |
| `rag-paid-011` | 3B | B | Restates the manual-payment paragraph as if it were setup steps. |

## Identity tool over-calling (8 non-identifying messages, current tool description)

The tool description is unchanged since the initial commit, so it is the original.
The exact 8 messages of the earlier ablation were not recorded, so this set is new
("hey there", "what's up", "I need help with my store", a pricing question, "hello, is
anyone there?", "my checkout page is broken", "who am I talking to?", "I forgot which
email I signed up with").

| | 3B | 8B |
|---|---|---|
| Called `user_info_db_search` | 8/8 | 8/8 |
| With a real account it was never given (`john@doe.com`) | 3/8 | 0/8 |
| Guard rejected | 8/8 | 8/8 |

The guard holds for both. The 8B invents placeholder strings ("user email address or
phone number"), not plausible real accounts, which is the less dangerous shape.

## Cost

Fixed 12-entry workload (4 identification, 4 rag, 4 callback), warmed, sequential:
**3B 63 s (5.3 s/entry), 8B 82 s (6.8 s/entry)**, about 1.3x. This understates the
8B's real cost, because it skips the second tool call on most identifications. The
model is 4.9 GB against 2.0 GB on disk. A full-run wall-clock was not used: the turn
log windows for the two full runs could not be separated cleanly (136 and 113
conversations found, 122 expected).

## Caveats and deviations from the plan

- **Grader.** One reader, and it is the same assistant that ran the experiment, not a
  human. Blinding hides which model wrote each answer, but the sheet showed which KB
  tier was retrieved, which correlates with the 8B on premium logins.
- **Graded against the KB tier actually retrieved**, not the user's true tier. The 8B
  served the free KB to all 19 premium-login entries; wrong-tier answers are counted
  by tier leakage, not here.
- **3B rate differs from earlier documents.** This grade puts the 3B at 1/51 clear
  hallucinations, against about 10% (2/21) for the held-out set in
  `Rag-HeldOut-Results-2026-09-19.md`. That earlier run was before fixes #16/#17, and
  the 51 include entries those fixes were tuned on, but the grades are also one
  reader's judgment. The H+B upper bound (14%) is closer to the earlier figure. The
  comparison between models is the safer reading than the absolute rate.
- **The fresh 3B run does not match `Precision-FullEval-2026-09-19.md`** on the same
  code (callback recall 100% vs 97%, precision n 39 vs 38). Not investigated;
  temperature 0 does not guarantee identical output here.
- **One full run per model**, as planned. The 8B failure mechanism was reproduced 3/3
  in isolation and 3/3 through the pipeline.
- **Model-only intent check** used a greeting-only history, so it differs from the
  pipeline's (the 3B shows 1 false trigger there against 2 in the full run).
- **Tuned to the 3B.** Prompts, guards and patterns were developed around 3B
  behaviour, which favours it. The 8B was not given a chance to have its own tool-call
  handling fixed; a text-form tool call parser could change the identification result.
- OpenAI models were not tested.
