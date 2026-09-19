# KB rewrite + stricter prompt — results (Sprint 2, issues #5 and #6)

Follows `Triage-2026-09-19.md` (cause is generation, not retrieval) and
`Prompt-Experiment-2026-09-19.md` (a stricter prompt alone fixes only
`rag-oos-002`). This is the last lever from that plan: rewrite the KB text the
model can't use reliably.

## What changed in `assets/`

| File | Change | Why |
|---|---|---|
| `free/locations.txt` | The tier limit now leads and is unambiguous ("only a single location... cannot set up multiple locations... multiple locations are available only with a paid subscription"). Removed the tier-neutral "maximum number of locations depends on your plan" and "split orders across multiple locations" sentences, the "deactivate" note, and the custom-app/multiple-locations paragraph. Reworded "only an online store you manage" (the source of an invented qualifier in an earlier answer). | Old text stated the limit once, then contradicted or diluted it |
| `free/pos.txt` | Replaced the how-to-sell-in-person text with a short, consistent statement: free = online only; in-person selling and POS hardware need a paid subscription. | The file taught in-person selling and then, in one ungrammatical last line, said free can't do it (#6) |
| `paid/locations.txt` | States "paid subscription: multiple locations, not limited to a single location". Removed "the maximum number of locations depends on your plan". | That sentence produced evasive answers (`rag-paid-001`) and "you are limited to one location" for a paid user |

Editing required the new `scripts/reindex_kb.py`: `--check` flagged exactly these
three files as stale (free 2 chunks, paid 1) and exited 1 before the rebuild.
Chunk counts are unchanged (free 14, paid 15).

## Screen before the full run (regex, 3 runs each, production prompt)

| Question set | Old KB | New KB |
|---|---|---|
| 15 tuned `rag-*` entries | 30/45 (67%) | 42/45 (93%) |
| 5 held-out questions | 6/15 (40%) | 12/15 (80%) |

Held-out questions were written before editing and never scored on the old
KB before this baseline: "Can I have a second warehouse location on my current
plan?" (free), "Is Shopify POS included in my subscription?" (free), "Can I add
a location for my pop-up store?" (free), "Can I set up locations for both my
warehouse and my retail store?" (paid), "Am I limited to one location on my
plan?" (paid). The old KB got three of these wrong, including telling a paid
user "Yes, you are limited to one location" and a free user "Yes, Shopify POS is
included". The two screen "failures" left in the new run (`rag-adv-004`, held-out
`H2`) were regex gaps ("isn't available", "does not include"); reading the
answers showed both correct. Per-entry: six answers flipped 0/3 -> 3/3
(`free-004`, `paid-001`, `adv-001`, `adv-002`, `H3`, `H5`); none regressed on the
screen.

## Full 38-entry eval (`Baseline-2026-09-19-sprint2.md`)

All six machine-scored metrics are identical to the Sprint 1 post-fix run, so
nothing regressed: identification 100% (n=6), fails-safe 100% (n=5), retrieval
recall@k 100% (n=12), tier leakage 0% (n=12), callback recall 100% (n=7),
callback precision 100% (n=7). No crashes.

## Hallucination rate, hand-graded (the actual metric)

Same rubric as `Hallucination-Grading-2026-09-19.md`, all 15 `rag-*` answers read
against the KB text.

| Grade | Sprint 1 (old prompt + old KB) | Sprint 2 (new prompt + new KB) |
|---|---|---|
| Grounded and correct | 9 | 14 |
| Grounded but unresponsive (not counted) | 3 | 0 |
| **Hallucinated** | **3 (20%)** | **1 (6.7%)** |

Fixed: `rag-adv-001`, `rag-adv-002` (now "No... only a single location"),
`rag-oos-002` (now the exact "I don't have information about that in our help
center."), and the unresponsive `rag-free-004`, `rag-paid-001`, `rag-adv-004`.

**Still hallucinated: `rag-free-002`** ("How do I get paid from my sales?"). It
says *"If you're using a third-party payment provider, payouts are sent to the
same bank account used for Shopify Payments."* That sentence is at
`free/payments.txt:18`, but it is about Shop Pay Installments / Affirm payouts;
for third-party gateways line 9 says you won't see payout information in your
admin. Mild misattribution, not an invented fact.

**This one is a side effect of the KB change, not pre-existing.** With the new
prompt and the old KB, the same question gave a grounded answer ("...check your
pay period to view when you receive payouts"). My untested guess is that
shrinking `free/pos.txt` freed a top-4 retrieval slot, so a different payments
chunk (containing the Affirm passage) now reaches the model. It is also
unstable: 2 distinct answers over 3 screen runs.

**Target status: not met.** Target is <=5%; at n=15 one wrong answer is 6.7%, so
only 0/15 meets it. Improvement over Sprint 1 is large (20% -> 6.7%).

## Caveats

- **The KB was edited after seeing the failures.** The five previously failing
  entries improved in part because the text was written to be unambiguous about
  exactly those topics. The held-out questions are the fairer evidence, but they
  are the same topics (locations, POS), so they show generalization to nearby
  questions, not to unseen ones. Both sets were written by the person who also
  wrote the fix.
- **n=15, one run for the hand grade**, and the model is not fully stable (see
  `rag-free-002`). One answer moves the rate by 6.7 points.
- **The regex screen mis-scored two correct answers** (see above), so its numbers
  are for iteration only; the hand grade is the result.
- **Golden-set questions were not changed**, but with n=15 the <=5% target is
  almost too coarse to test. A larger `rag-*` set would give a usable estimate.
- The KB text is derived from third-party (Shopify) help content (#14). These
  edits shortened the free-tier POS text, but the licensing question is open.

## Open items

- `rag-free-002` misattribution (mild). Candidate fixes: separate the Shop Pay
  Installments passage from general payout text in the free KB, or drop it from
  the free tier if free-tier customers can't use it. Treat as whack-a-mole risk
  with a 3B model: re-score everything after any further change.
- Grow the `rag-*` golden set so a <=5% target is measurable.
