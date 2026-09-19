# Verification of the #16 and #17 fixes — pre-registered criteria and baseline

Issues: #16 (free KB contradicts itself on manual payments), #17 (model invents
UI steps for "how do I..." questions). This file is written **before** either
fix so the pass/fail bar cannot move afterward. The post-fix result is appended
below once it exists.

## Design: development set vs test cohort

- **Development set** = the 36 `rag-*` entries that existed before this branch.
  Both known failures (`rag-free-006`, `rag-oos-007`, `rag-adv-006`) are in
  it. Prompt and KB edits may be iterated against these.
- **Test cohort** = the 15 entries added in commit `0b350ca` (2026-09-19
  11:43), written from the KB text and committed before any run. They are
  baselined once below (before any fix) and run **once** after the fixes.
  They must not be used to tune.

## Pre-fix baseline on the test cohort (current `main` prompt + KB)

Machine-scored: retrieval recall@k 100% (n=11), tier leakage 0% (n=11), no
crashes. Raw report: `Verify-Baseline-PreFix-2026-09-19.md`. Hand-graded against
the KB text (same rubric as `Hallucination-Grading-2026-09-19.md`):

| Grade | Count | Entries |
|---|---|---|
| Correct and grounded | 8 | free-011, 013, 014; paid-011, 012, 013, 014; adv-010 |
| **Hallucinated** | **4** | `rag-oos-009` (invented "Settings > Payments > Add payment provider"), `rag-oos-010` (invented "Products > Add product"), `rag-oos-012` (invented 5-step password reset), `rag-free-012` (mild: says the copyright-notice form is "in your store admin"; the KB says only "online form", and "store admin" is from the counter-notice form) |
| Wrong because of the #16 contradiction | 2 | `rag-adv-009`, `rag-adv-011` (both answer "Yes" to a free user asking about bank transfers / money orders) |
| Borderline, not counted | 1 | `rag-oos-011` (card reader: no invented steps or menu paths, but embellishes "a list of supported card readers in the Hardware section" and doesn't say it lacks the steps) |

Baseline fabrication rate: **4/15 = 26.7%**; with the two KB-caused errors 6/15
= 40%. Both problems reproduce on questions written without seeing the model's
outputs.

The paid-tier guard works before any fix: `rag-paid-013` (same wording as
`rag-adv-011`) correctly answers "Yes" for a paid user.

## Success criteria (fixed now, before the fixes)

**#17, no invented steps.** On the 10 procedural entries (free-011..014,
paid-011, paid-012, oos-009..012): **0 answers that state menu paths, buttons
or steps absent from the KB**, and the covered procedures (free-012, free-013,
free-014) must still be answered, not refused.

**#16, manual payments.** `rag-adv-009` and `rag-adv-011` answer that manual
payments are **not** allowed on the free plan; `rag-adv-010` stays correct; and
`rag-paid-013` and `rag-paid-014` **stay correct** (the fix must not
over-restrict the paid tier).

**No regression.** Development set: no answer that was correct before becomes
wrong (hand-checked wherever the answer text changes); full eval: retrieval
recall and tier leakage stay at 100% / 0%, and callback recall/precision at
100% / 100%; unit tests pass.

**Overall.** Hallucination rate reported on the test cohort with counts and the
three-view breakdown used elsewhere. Anything that misses a criterion is
reported as a miss.

## Caveats set in advance

- n=15, single run, hand-graded by the same person who wrote the questions and
  the fixes; `rag-free-012` and `rag-oos-011` are judgment calls.
- A 3B model is not fully stable across runs; a criterion met once is evidence,
  not proof.
- The test cohort was written knowing the KB's structure.
