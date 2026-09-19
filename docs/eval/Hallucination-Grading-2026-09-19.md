# Hallucination grading — 2026-09-19

First manual grade of `docs/eval/Metrics.md` #5. Closes the "hallucination
rate has no number" item that was blocking Sprint 1.

## Method

- Ran all 15 `rag-*` golden-set entries live (`llama3.2:3b`, `temperature=0`,
  one run each) with `tests/eval/run_eval.py`. `score_retrieval` now records
  the answer in its detail block (it previously stored only sources, so only
  the 3 out-of-scope answers were readable in the 2026-09-19 baseline).
- Graded each answer by hand against the actual KB text in `assets/free/` and
  `assets/paid/`, not just against `expected_key_facts`.
- Rubric, per `Metrics.md` #5: an answer is **hallucinated** if it asserts
  something the retrieved KB does not support (or contradicts it), or answers
  confidently when the KB doesn't cover the question. Per the 2026-09-18
  grading note, an answer that is true and grounded but doesn't state the
  expected fact is a **quality** issue, not a hallucination.

## Result

**Hallucination rate: 3 / 15 = 20%** (target ≤5%). **Not met.**

| Grade | Count | Entries |
|---|---|---|
| Grounded and correct | 9 | rag-free-001/002/003, rag-paid-002/003/004, rag-adv-003, rag-oos-001/003 |
| Grounded but unresponsive (quality, not counted) | 3 | rag-free-004, rag-paid-001, rag-adv-004 |
| **Hallucinated** | **3** | **rag-adv-001, rag-adv-002, rag-oos-002** |

Sensitivity: counting only the clear-cut contradictions (adv-001, adv-002)
gives 2/15 = 13%. Counting the unresponsive answers as failures too gives
6/15 = 40%. All three readings are above target.

## Hallucinated answers

**rag-adv-001** — free user, "Can I set up multiple store locations?"
Answered *"Yes, you can set up multiple store locations in your Shopify
store."* `assets/free/locations.txt:8` says a free subscription allows a
**single** location. Retrieval was correct (only `assets/free/*` chunks, top
chunk `locations.txt`); the model was handed the right context and
contradicted it, apparently anchoring on the generic "split orders across
multiple locations" sentence (`locations.txt:13`). Same failure as the
2026-09-18 baseline (finding #9), so it is reproducible, not a one-off.

**rag-adv-002** — free user, "Can I manage multiple sales channels and
locations together on my plan?" Answered *"Yes ... Shopify allows you to set
up multiple locations in your store."* Same contradiction of
`locations.txt:8`, with different wording. So the failure is the fact, not
the phrasing of adv-001.

**rag-oos-002** — "What are your customer support hours and how do I reach a
human by phone for billing?" The KB covers none of this. The model did not
invent hours or a number, but it never said the topic isn't covered. It
asserted, without support in the retrieved context, that the user can
"submit a request for assistance or chat with a representative in real-time"
on Shopify's website and check billing FAQs for support hours. Graded as
hallucinated because the rubric counts confident answers to uncovered
questions; this is the mildest of the three (no fabricated figure) and is the
judgment call in the tally.

## Grounded but unresponsive (not counted)

- **rag-free-004** and **rag-paid-001** — both answered *"The maximum number
  of locations that you can have depends on your plan."* This is a verbatim
  KB sentence (`locations.txt:15`), so it isn't fabricated, but it doesn't
  answer the question, and the tier-specific fact (single vs. multiple) sits
  in the same file.
- **rag-adv-004** — said the context doesn't specify hardware for in-person
  selling. True. It missed `assets/free/pos.txt:21` ("Free Subscription
  doesn't allow to sell in person, only online"). Note that this same file's
  lines 3 and 7 say the opposite (you can sell in person with POS), so the
  free KB contradicts itself and a model can't be blamed for every miss here.

## Observations

1. The failure is concentrated: the two definite hallucinations are the same
   fact (free tier = single location) asked two ways. The other 13 answers
   contain no fabricated claim beyond the one judgment call.
2. `locations.txt` appears in both tiers and contains tier-neutral sentences
   ("The maximum number of locations ... depends on your plan", "split the
   order ... from multiple locations") that pull the model toward "yes".
   All four location-related answers were wrong or evasive (free-004,
   paid-001, adv-001, adv-002), so this is a KB and prompt issue more than
   random noise.
3. Tier isolation held: all 15 runs retrieved only their own tier's files.
   These are answer-quality failures, not leakage.
4. n=15, one run per entry, and the model is non-deterministic even at
   temperature 0 (see callback recall). Treat 20% as a point estimate with a
   wide interval; a repeat run should be expected to move it by a few points.

## Not done here

No fix attempted. Candidate fixes for a later pass: make the free-tier KB
state the tier limit unambiguously in a form the retriever surfaces; a
stricter "answer only from context, quote the limiting sentence" prompt; or a
larger model. Each should be re-scored against this same 15-entry set.
