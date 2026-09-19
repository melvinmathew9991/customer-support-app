# Held-out `rag-*` results — unbiased hallucination estimate (Sprint 2, issue #5)

The 15 original `rag-*` entries were tuned against: the prompt and KB were edited
after seeing their failures, and with n=15 one wrong answer is 6.7%, so the <=5%
target was only reachable at 0/15. This adds 21 entries written from the KB text
alone and committed (`a997791`) **before any model run**, then runs them once
against the current prompt and KB (`Rag-HeldOut-2026-09-19.md` is the raw report).

## Machine-scored (harness)

Retrieval recall@k **100%** (n=16, target >=90%), tier leakage **0%** (n=16,
target 0%, includes the reverse case `rag-adv-008`). No crashes. Retrieval and
tier isolation hold on unseen questions across all KB files, including the
compliance file the tuned set barely touched.

## Hallucination, hand-graded (all 21 answers read against the KB text)

Same rubric as `Hallucination-Grading-2026-09-19.md`: an answer is hallucinated
if it asserts something the KB does not support, or answers an uncovered
question from general knowledge.

| Grade | Count | Entries |
|---|---|---|
| Correct and grounded | 17 | free-005/007/008/009/010, paid-005 through paid-010, adv-005, adv-008, oos-004/005/006/008 |
| **Hallucinated** | **2** | `rag-free-006`, `rag-oos-007` |
| Wrong because the KB contradicts itself | 1 | `rag-adv-006` |
| Correct conclusion, unsound reasoning | 1 | `rag-adv-007` |

| View | Rate |
|---|---|
| Fabrication only (hallucinated) | **2/21 = 9.5%** |
| + KB-caused wrong answer | 3/21 = 14.3% |
| + unsound reasoning | 4/21 = 19.0% |

**Target (<=5%): not met on any view.** The 6.7% reported for the tuned 15 was an
optimistic point estimate; on questions not tuned against, fabrication is about
10%. (Pooled with the tuned 15, 3/36 = 8.3% by fabrication, but the pool mixes a
tuned and an untuned sample and shouldn't be read as one estimate.)

### The failures

- **`rag-free-006`** ("My bank account details changed. How do I update where I
  get paid?"): answered with "log in to your Shopify admin, go to Settings >
  Payments > Bank account, and click 'Edit'". The KB (`free/payments.txt:14`)
  says only that you can update the details "in your Shopify Payments
  settings". The click path is invented. Verified: no such path appears
  anywhere in `assets/`.
- **`rag-oos-007`** ("How do I cancel my subscription?"): answered with invented
  steps ("Settings > Account > Cancel Subscription"). The KB has nothing on
  cancelling (verified by search). The prompt says to reply only "I don't have
  information about that in our help center." and to use no general
  knowledge; the model ignored it.
- **`rag-adv-006`** (free user asks about email money transfers in Canada):
  "No, with a free subscription, you can only accept manual payments outside of
  your online checkout, such as money orders or bank transfers." The "No" matches
  the expected outcome, but the rest asserts that free users can accept money
  orders and bank transfers. That comes from `free/payments.txt:8`, which
  contradicts line 46 ("Manual payment methods are not allowed on free
  subscription"). This is a **KB defect**, flagged in the entry's notes before the
  run; the model is quoting one of two conflicting lines.
- **`rag-adv-007`** (free user: "I run shops in two different cities. Can one
  store on my plan manage both?"): says no, but for the wrong reason: it infers
  the user is selling in person ("that implies in-person selling") and never
  states the single-location limit. The conclusion is right and nothing is
  fabricated about the KB, but the reasoning is an unsupported assumption about
  the user.

### A pattern (weak evidence)

Both fabrications are procedural "how do I <do an admin task>" questions where
the KB has a partial answer or none. Of the four such questions in this set
(`free-006`, `oos-004`, `oos-005`, `oos-007`), two were fabricated; the other two
correctly refused. General knowledge about admin UI steps seems to leak in even
under a prompt that forbids it. With n=4 this is a hypothesis, not a finding.

## What the new set changes

- **The <=5% target is not currently met**, and the honest estimate is closer to
  10%. The tuned-set result should not be quoted alone.
- **Two new KB/prompt items** (not fixed here): the manual-payments contradiction
  in `free/payments.txt` (lines 8 vs 46), and the procedural-question leakage.
- **The set is now 36 `rag-*` entries** (59 in the full golden set). At n=36 one
  wrong answer is 2.8%, so <=5% needs at most one wrong answer; still coarse but
  usable.

## Caveats

- **These entries stop being held-out the moment they are used to tune.** If the
  next step edits the prompt or KB to fix `free-006`/`oos-007`/`adv-006`,
  re-scoring these same entries will be optimistic again. Keep a further set
  unseen, or split the golden set into development and test cohorts.
- One run per entry, hand-graded once, by the same person who wrote the
  questions and the fix. The model is not fully stable (see `rag-free-002` in
  `KB-Rewrite-Results-2026-09-19.md`).
- The questions were written knowing the KB's structure, so they are unbiased
  with respect to the model's outputs but not to my knowledge of what is in the
  KB.
- Two grade calls are judgment: `adv-006` (KB-caused, counted separately) and
  `adv-007` (correct conclusion, not counted as hallucinated in the headline).
