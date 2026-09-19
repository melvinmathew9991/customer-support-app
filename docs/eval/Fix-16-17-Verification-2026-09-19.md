# Verification of the #16 and #17 fixes — pre-registered criteria and baseline

Issues: #16 (free KB contradicts itself on manual payments), #17 (model invents
UI steps for "how do I..." questions). This file is written **before** either
fix so the pass/fail bar cannot move afterward. The post-fix result is appended
at the end.

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

---

# Post-fix results (fixes committed in `d8b0cd0`, 2026-09-19 11:55; run at 11:55-12:11)

One full 74-entry eval, run once after the fixes, so the test cohort was run a
single time. Raw report: `Baseline-2026-09-19-fix-16-17.md`. The fixes: the
`free/payments.txt` line 8 edit (#16), prompt rule 5, and the `invents_steps()`
guard in `RetrievalNode._predict` (#17).

## Machine-scored metrics: no regression

Identification 100% (n=6), fails-safe 100% (n=5), retrieval recall@k 100%
(n=39), tier leakage 0% (n=39), callback recall 100% and precision 100% (n=7).
No crashes. 105 unit tests pass.

## Test cohort, graded against the criteria written above

| Grade | Baseline | Post-fix | Post-fix entries |
|---|---|---|---|
| Correct and grounded | 8 | **11** | free-011, 013, 014; paid-011, 013, 014; adv-009, 010, 011; oos-010, 012 |
| **Hallucinated** | 4 | **2** | `rag-free-012`, `rag-oos-011` |
| Wrong because of the #16 contradiction | 2 | **0** | (adv-009 and adv-011 fixed) |
| Borderline, not counted | 1 | 1 | `rag-oos-009` |
| Grounded but unresponsive | 0 | 1 | `rag-paid-012` |

Fabrication rate on the untuned cohort: **4/15 = 26.7% -> 2/15 = 13.3%**
(counting the borderline, 3/15 = 20%; baseline with KB-caused errors, 6/15 =
40%). **The <=5% target is not met.**

### #16 (manual payments): criteria met

`rag-adv-009` and `rag-adv-011` now answer that manual payments are not allowed
on the free plan (both said "Yes" before), `rag-adv-010` is still correct, and
`rag-paid-013` and `rag-paid-014` are still correct, so the paid tier was not
over-restricted.

### #17 (invented steps): criteria NOT met

The criterion was 0 invented steps on the 10 procedural entries; the result is
2/10.
- **Fixed**: the click-path fabrications. `rag-oos-010` (add a product) and
  `rag-oos-012` (reset a password) now give the "I don't have information..."
  reply. Covered procedures (`free-012`, `013`, `014`) are still answered.
- **Still fabricated**:
  - `rag-free-012` says the copyright form is "in your store admin". Unchanged
    from baseline; the KB says only "online form", and "store admin" belongs to
    the counter-notice form. It has no navigation wording, so the guard cannot
    see it.
  - `rag-oos-011` (card reader) now states setup steps: "set up your card reader
    in the Shopify POS app and link it to your Shopify admin". At baseline I had
    it as borderline (it mostly restated the KB); this answer states steps
    outright, so it is counted. No click/menu wording, so the guard cannot see it.
- **Borderline**: `rag-oos-009` went from an invented "Settings > Payments > Add
  payment provider" path to "in the Payment providers area of your Shopify
  admin". That phrase is in the KB (`payments.txt:2`), but using it for *enabling
  Shopify Payments* is an inference.
- **Cost**: `rag-paid-012` now refuses where it previously gave a circular but
  grounded answer; the guard blocked invented steps there. Safe, but less
  helpful.

## What the guard did

It fired on 4 turns in this run: "How do I cancel my subscription?", "How do I
add a new product to my store?", "How do I reset my admin password?", and "How do
I add a location to my POS device?". In each the model had produced click-path
steps absent from the context, so all four blocks were correct; there were no
false positives. It only catches navigation wording (click, navigate, tap, "A >
B"); the two remaining fabrications use other wording.

## Regression check on the development set

Compared with the answers on merged `main`: 22 of 36 identical, 14 changed, none
worse. `rag-free-006`, `rag-oos-007`, and `rag-adv-006` are fixed, `rag-free-002`
lost its earlier mild misattribution, and the rest are shorter rewordings that
stay grounded. `rag-adv-007` still reaches the right conclusion by an unsound
argument (unchanged). The development set now shows 0 fabrications in 36, but it
was tuned against, so that figure is optimistic and is not the estimate.

## Reading the result

- The two problems the issues describe are largely addressed: the KB
  contradiction is fixed and click-path fabrication is blocked.
- The overall fabrication rate is still about 13% on unseen questions, and the
  remaining failures are ones a navigation-wording guard cannot catch: a
  misattributed location, and steps described in plain prose.
- Pooling the tuned 36 with the untuned 15 (2/51 = 3.9%) would look like a pass
  but is not a valid estimate.

## Caveats

- n=15, one run, hand-graded by the author of the questions and the fixes.
  `rag-free-012`, `rag-oos-009` and `rag-oos-011` are judgment calls; counting
  `oos-011` as hallucinated is a stricter reading than the baseline's.
- The test cohort was run once and not tuned against, but is now a used set:
  further fixes need a fresh cohort.
- A single run of a 3B model that is not fully stable.
