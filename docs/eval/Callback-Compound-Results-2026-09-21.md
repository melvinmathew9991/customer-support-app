# Callback veto and compound phrasings (#33) — 2026-09-21

Model `llama3.2:3b` via Ollama, temperature 0, one run per entry. Harness: `tests/eval/run_eval.py`.

## Problem

`CallCustomerEdge.check()` rejected any message that matched the do-not-call pattern before
looking for a request, so a message that declined one thing and asked for another
("Never call me before 9am, but do call me on 0452 333 666 after.") was refused without the
model being asked.

## Method

The cohort was written and committed **before** any code change (`91bce03`): 12 entries,
`call-059` to `call-070`. Not to be tuned against.

| Entries | What they are |
|---|---|
| `call-059`..`063` | Real requests that also decline something (5) |
| `call-064`, `call-065` | Controls: the decline does not use a call word (2) |
| `call-066`..`069` | Plain declines that offer a number (4) |
| `call-070` | Hard case: a decline plus "you can call me back only if the email bounces", labelled a non-request |

The fix removes each decline from the message before looking for a request, so "never call me
on X" has nothing left, while "never call me before 9am, but do call me on X" keeps its second
request. Clause splitting and sending mixed messages to the model were both rejected: almost
every decline also contains "call me", so "both patterns match" cannot tell the cases apart.

## Results

| | Before | After |
|---|---|---|
| Cohort recall (7 requests) | 2/7 (29%) | **7/7 (100%)** |
| Cohort non-requests rejected (5) | 5/5 | **4/5** (`call-070` now false-triggers) |
| Callback recall, all 44 requests | 39/44 (89%) | **44/44 (100%)** |
| Callback precision, all entries | 95.1% (39/41) | **93.6% (44/47)** |
| Older `call-*` and `rag-oos-*` entries | `call-042`, `call-047` fail | the same two fail, nothing new |

The three false triggers are `call-042` and `call-047` (already known, #23) and `call-070`.
Phone extraction was 100% (44/44).

## Costs and caveats

- **`call-070` is a real trade-off.** A message that declines calls and then offers to be called
  "only if" something happens is now treated as a request. Guarding on "only if", "unless" and
  "in case" would fix this entry but would be tuning to it; it would stop being held out and
  would need a new cohort.
- Precision fell from 95.1% to 93.6% because of `call-070` alone. Without the cohort the older set
  is unchanged at 94.9% (37/39), which already missed the >=95% target because of `call-042` and
  `call-047`.
- Written by the author of the fix, one run of a 3B model, n=12: five recovered requests is a
  clear signal, one false trigger is a single observation.
- A related gap the cohort did not cover: "can't call me" is not a decline pattern, so
  "You can't call me on X" is treated as a request. Not addressed here.
- The rag-oos entries only feed the precision denominator here; their answers were not
  re-graded.
