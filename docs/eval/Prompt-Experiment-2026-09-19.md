# Answer-prompt experiment — 2026-09-19

Issue #5. Follows `docs/eval/Triage-2026-09-19.md`, which found that the six bad
answers come from the generation step, not retrieval or chunking.

## Method

Same 15 `rag-*` golden questions, real tier retrievers (persisted Chroma, top-4
chunks), real model (`llama3.2:3b`, `temperature=0`), 3 runs per question per
variant. Only the system prompt changed. Answers were scored with a regex
screen per entry (required key fact present, forbidden claims absent), not by
hand.

**Screen calibration:** under the old prompt the screen failed exactly the six
answers graded by hand in `Hallucination-Grading-2026-09-19.md` (`rag-free-004`,
`rag-paid-001`, `rag-adv-001`, `rag-adv-002`, `rag-adv-004`, `rag-oos-002`), each
3/3, and passed the other nine. All variants gave 3/3 identical outcomes per
entry, so the model is stable at temperature 0.

## Results

| Variant | Screen pass | Fails (each 3/3) |
|---|---|---|
| V0 old prompt | 27/45 (60%) | free-004, paid-001, adv-001, adv-002, adv-004, oos-002 |
| **V1 strict** (adopted) | **30/45 (67%)** | free-004, paid-001, adv-001, adv-002, adv-004 |
| V2 = V1 + "quote the sentence you used" | 27/45 (60%) | V1's five, plus paid-003 |
| V1 with only the top-2 chunks | 30/45 (67%) | same five as V1 |

V1 rules: answer only from context; the context is the customer's own plan; state
applicable limits plainly; never claim something is possible unless the context
says so; if the context lacks the answer reply exactly "I don't have information
about that in our help center." with no invented contact channels; 1-3 sentences.

## What the results say

- **V1 fixes `rag-oos-002`** (previously an ungrounded answer suggesting websites
  and live chat) and breaks nothing that passed. Adopted in
  `RetrievalNode._SYSTEM_PROMPT`.
- **A stricter prompt is not enough for the location questions.** `rag-adv-001`
  still answers "Yes, you can set up multiple store locations" and V1 even adds
  an invented qualifier ("...but only for online stores you manage"). The
  deciding sentence is in the top chunk (see the triage) and the model still
  can't use it.
- **The context-noise hypothesis did not hold**: cutting to two chunks changed
  nothing.
- **Quoting made things worse** (V2): it regressed `rag-paid-003` and, for
  `rag-free-004`, quoted an irrelevant sentence ("Locations that you deactivate
  don't count toward your location limit").
- Remaining failures all involve KB text that is ambiguous for a small model:
  `locations.txt` states the tier limit in one line surrounded by tier-neutral
  sentences ("depends on your plan"), and `free/pos.txt` contradicts itself
  (#6). That points at KB wording as the next lever.

## Caveats

- The screen is a regex heuristic tuned to these 15 entries. It reproduced the
  hand grades here, but a pass is not a hand-graded pass; the final numbers
  must come from a manual grade.
- Only 15 questions. The prompt was chosen against the same questions it is
  scored on, so 67% (and the fixed `rag-oos-002`) overstates how it would do on
  unseen questions.
- Single model, single temperature.
- This measures answer correctness/grounding only; other metrics
  (identification, callbacks) don't touch this prompt, but the full 38-entry
  eval must still be re-run to confirm no regression.
