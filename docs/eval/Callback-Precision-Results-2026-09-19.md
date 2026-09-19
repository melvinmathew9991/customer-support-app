# Callback precision results (Sprint 2, issue #23)

Issue #23: the callback intent check false-triggered on numbers offered for another
purpose (precision 85% vs the >=95% target). **The target is not met on unseen
messages: precision went from 67% to 83% on a held-out cohort, with recall
unchanged.** Reports: `Precision-Cohort-Baseline-run{1,2,3}-2026-09-19.md`
(unchanged code), `Precision-Cohort-PostFix-2026-09-19.md`,
`Precision-FullEval-2026-09-19.md`.

## Method

1. 22 entries (`call-037` to `call-058`: 12 negatives that contain a number but do not
   ask for a call, 10 varied positives) committed at 21:55 (`c6dd326`) before any run,
   and held out from every design decision.
2. Baseline on the unchanged code, 3 runs.
3. Candidate wordings and designs scored only on the entries already in the set
   (`call-001` to `call-036`, the ones with a number: 27 positives, 6 informative
   negatives), one model call per message, with a scratch harness that swaps the
   condition in memory (not committed). It reproduces the pipeline's known state
   exactly for the current wording (3 false triggers, `call-033` missed).
4. One change committed (`280934d`, 22:03), the cohort run once, then the full eval.

## Candidates on the existing entries (never on the cohort)

| Candidate | Precision | Recall |
|---|---|---|
| Current wording | 90% (3 false triggers) | 96% |
| Stricter wording with explicit "answer NO if..." cases | 100% | **11%** |
| Short wording only | 100% | 82% (5 missed) |
| Short wording plus worked examples | 93% | 52% |
| Multiple-choice intent (callback / asking about a number / changing details / other) | 100% | 48% |
| **Explicit-request check, then the short wording** | **100%** | **96%** (only `call-031` missed) |

The recall-for-precision trade seen in Sprint 1 is real: every wording change alone
lost recall. Four of the five misses of the short wording were plain requests ("Can
you call me?", "please give me a call") that the model rejects once a number is in the
message, so they are now decided without it. These numbers flatter the last row: the
request patterns were written while reading these entries, and only 6 negatives here
are informative.

## What changed

`CallCustomerEdge.check()` (after the existing 6-digit pre-check):
1. A message that asks not to be called ("don't call", "do not call", "no calls",
   "never call") is rejected, without the model.
2. An unambiguous request ("call me", "ring me", "phone me", "give me a call",
   "callback", "call this number", "someone/an agent should call") is accepted,
   without the model.
3. Otherwise the model decides, with a shorter condition: "Does the user ask a
   support agent to call them? Only mentioning, giving, changing or asking about a
   phone number is not a request to be called."

"Call us" is deliberately not a pattern, so a user quoting a site's "call us on ..."
is left to the model.

## Result on the untouched cohort

| | Unchanged code (3 identical runs) | After the change |
|---|---|---|
| False triggers (12 negatives) | 5 | **2** |
| Precision | 67% (10/15) | **83%** (10/12) |
| Recall (10 positives) | 10/10 | 10/10 |
| Phone extraction | 10/10 | 10/10 |

Fixed: `call-038` (confirm a saved number), `-040` (spam calls), `-043` (export a
customer's number), `-045` (remove an old number). Not fixed: `call-042` ("What
format should an Australian number like +61 452 883 210 be in for the checkout
form?"). **New:** `call-047` ("Do you offer phone support? I saw 1300 224 907 listed
on a third-party site.") was correct before and now false-triggers. Both remaining
failures are questions about phones, which the 3B model keeps reading as requests.

**Variance:** the three baseline runs were identical, entry by entry. The pipeline is
deterministic at temperature 0 on these entries, so repeat runs here add nothing.

## Full eval (122 entries)

| Metric | Before (`Extraction-Leak-FullEval`, 100 entries) | After |
|---|---|---|
| Callback recall | 96% (26/27) | 97% (36/37); missed `call-031` |
| Callback precision | 90% (26/29) | 94.7% (36/38) |
| Phone extraction | 100% (26/26) | 100% (36/36) |
| Identification / fails-safe | 100% / 100% | 100% / 100% |
| Retrieval recall / tier leakage | 100% / 0% | 100% / 0% |

The harness prints the precision as "95%"; it is 36/38 = 94.7%, just under the
target. **Do not read this as the target being met.** The blended figure includes the
existing entries that shaped the change (`call-023`, `-025`, `-026`, `-033` now pass
because of it), and the sets differ in size. The untouched cohort's 83% is the honest
number. The 14 unscored entries were compared with the last full run: all identical.

## Not fixed / caveats

- `call-042` and `call-047` (above). Any further tuning needs a new cohort; this one
  is now seen.
- I wrote the negatives knowing the earlier failure shapes, so they may be easier
  than real traffic, and 12 negatives is a small sample (one entry is 8 points).
- The request patterns are English phrases and will miss other wordings; "Will
  someone call me back?" would be accepted as a request. `call-031` ("I'd rather talk
  this through by phone. My number is ...") is still missed, by design: indirect
  requests depend on the model.
- The remaining lever is the model's judgment on phone-related questions. A larger
  model, or a stronger deterministic filter for questions ("?" plus a phone word and
  no request pattern), are the next things to test, on a new cohort.
