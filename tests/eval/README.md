# Golden conversation set

`golden_set.json` is the hand-labeled ground truth Sprint 1's baseline (and
every later sprint's regression gate) is measured against. See
`docs/eval/Metrics.md` for how each field below feeds a specific metric.

This is a **draft structure** - one illustrative record per category, not
yet the full 30-50 conversations `docs/Sprints.md` scopes for Sprint 1.
Once the shape below is approved, the plan is to add more phrasing/topic
variations within each existing category rather than invent new ones,
so the category list stays the taxonomy every metric is defined against.

## Record schema

```jsonc
{
  "id": "unique-kebab-case-id",
  "category": "one of the categories below",
  "description": "one sentence: what this conversation is testing and why",
  "turns": ["each element is one user message, in order"],
  "turn_budget": 1, // max user turns allowed before the target behavior must happen
  "expected": {
    // present only when relevant to this record's category - see per-category notes
    "identified_user": { "name": "...", "email": "...", "subscription": "free|premium", "user_id": 0, "phone": "...", "language": "..." },
    "tier_used": "free|paid",
    "retrieval": {
      "expected_source_files": ["assets/<tier>/<file>.txt"],
      "expected_key_facts": ["short factual claim the answer should be consistent with"]
    },
    "callback_expected": false,
    "extracted_phone": "...",
    "final_node": "GreetingNode|AuthenticatedUserNode|CallCustomerNode",
    "expected_behavior": "free-text fallback for cases too irregular for the structured fields above (e.g. graceful-failure requirements)"
  },
  "notes": "why this case is in the set, or a known risk it's targeting"
}
```

Not every field applies to every category - an identification-only record
has no `retrieval` block, a RAG record has no `identified_user` block
(identification already happened in a prior turn and isn't being tested
again), etc. Leave irrelevant fields out rather than null-filling them.

## Categories (draft set covers one example of each)

| category | tests | metric(s) it feeds |
|---|---|---|
| `happy_path_identification` | clean email/phone resolves correctly in one turn | Identification success rate |
| `ambiguous_identification` | malformed input, then a retry that resolves | Identification success rate (ambiguous bucket) |
| `unknown_user_identification` | email/phone with no matching record | Fails-safe rate |
| `subscription_lookup_missing` | user found, but `user_subscription_db.py`'s mock data has no subscription row for them (this is real - see `user_id: "4"` in `tools/user_info_db.py`) | Fails-safe rate + tier-leakage risk (does the model silently guess a tier?) |
| `free_tier_question` | in-scope question, answerable from `assets/free/` | Retrieval recall@k, hallucination rate |
| `paid_tier_question` | in-scope question, answerable from `assets/paid/` | Retrieval recall@k, hallucination rate |
| `adversarial_tier_crossing` | a free user asks about a paid-exclusive feature | Tier-leakage rate |
| `out_of_scope_question` | question no KB file covers | Hallucination rate |
| `callback_request_explicit` | direct, unambiguous callback phrasing | Callback recall |
| `callback_request_indirect` | indirect/polite callback phrasing | Callback recall |
| `callback_false_trigger` | mentions "phone"/"call" but isn't requesting a callback | Callback precision |

## Known data quirks to account for when scoring (not bugs to fix here)

- `assets/free/compliance.txt` and `assets/paid/compliance.txt` are
  byte-identical - don't use compliance questions for tier-leakage cases,
  there's no observable difference to leak.
- `tools/user_info_db.py`'s `user_sub` list only has entries for
  `user_id` 1-3; `user_id "4"` (XYZ) exists in `user_info` but has no
  subscription row - this is what `subscription_lookup_missing` targets.
