# Sprint 1 — Evaluation metrics & targets

Defines what "measurable" means for this system, per `docs/Sprints.md`
Sprint 1. Each metric below is computed against `tests/eval/golden_set.json`
(see `tests/eval/README.md` for the record schema). No metric here is
scored yet - this document fixes the definition and target *before* the
harness is built, so the harness has an unambiguous spec to implement
against instead of ad hoc scoring decisions made while writing it.

## 1. Identification success rate

**What it measures:** does `UserInfoChainBasedEdge` resolve the correct,
complete `UserProfile` (name, email, subscription, user_id, phone,
language) within the conversation's `turn_budget`.

**Formula:**
```
correct_identifications / total_identification_conversations
```
A conversation counts as correct only if every field of the resolved
`UserProfile` matches `expected.identified_user` exactly (subscription
compared case-insensitively) - a right name with a wrong subscription is a
failure, not a partial success, since a wrong subscription is a
tier-leakage risk, not a cosmetic miss.

**Targets:**
- Well-formed input (`ident-001`, `ident-002` style): **≥95%**
- Ambiguous input requiring a retry (`ident-003` style): **≥80%** within
  the golden set's stated `turn_budget`
- Unknown/unresolvable users (`ident-004`, `ident-005` style): scored
  separately as **"fails safe" rate**, not identification success - see
  below.

**Fails-safe rate (unknown/partial identification):** % of
`ident-004`/`ident-005`-style conversations where the system does *not*
fabricate a `UserProfile` or crash, and instead asks the user to retry or
gives a clear "we can't find you" message. Since #37 this also covers what
happens after the retries run out: `ident-014` passes only if the conversation
ends at the "couldn't verify your account" message, with no answer and no
retrieval after it.
**Target: 100%** - this is a correctness gate, not a quality metric. Flagging
now: `ident-004` and `ident-005` in the draft golden set target a suspected
gap in `UserInfoChainBasedEdge`/`GreetingNode` - an unknown email or a user
with no subscription record may currently cause the edge to exhaust
retries and hand a non-`UserProfile` error payload to `AuthenticatedUserNode`,
which would crash on `user_profile.name`. Confirm during the baseline run
before assuming this metric passes.

## 2. Retrieval relevance (Recall@k)

**What it measures:** does the tier-selected retriever's top-k results
include at least one chunk from the question's expected source file(s).

**Formula:**
```
recall@k = (# questions where ≥1 expected_source_file appears in the
            top-k retrieved chunks' metadata) / total retrieval questions
```
`k` = 4, matching `Chroma.as_retriever()`'s default in
`tools/rag_responder.py`.

**Target:** **≥90%** recall@4, computed per tier (free and paid scored
separately, since the two KBs differ in size/content after the Sprint 0
fix to indexing).

## 3. Tier-leakage rate

**What it measures:** does a free user's retrieval ever pull a chunk whose
`source` metadata is under `assets/paid/`, or a paid user's retrieval ever
pull from `assets/free/`.

**Formula:**
```
leaked_conversations / total_conversations_with_retrieval
```

**Target: 0%.** Per `docs/Sprints.md`, this is a correctness bug, not a
quality regression - any non-zero result blocks the sprint's definition of
done, it doesn't just lower a score. `rag-adv-001` in the draft golden set
targets this directly (a free user asking a question phrased around a
paid-tier feature).

Note this metric is about the *retriever's source*, not the answer text -
`AuthenticatedUserNode._get_retriever()` already picks the retriever
deterministically by tier (see `agents/support.py`), so a leak here would
indicate a bug in that selection logic itself, which today looks correct
by inspection but has never been measured against adversarial phrasing.

## 4. Callback-intent precision/recall

**What it measures:** does `CallCustomerEdge` fire exactly when the user
is actually asking for a callback, and not otherwise.

**Formulas:**
```
recall    = (callback conversations where the edge fired AND extracted the
             correct phone_number) / total genuine callback conversations
precision = (conversations where the edge fired AND the user genuinely
             wanted a callback) / total conversations where the edge fired
```

**Targets:** recall **≥90%**, precision **≥95%** (a false positive creates
a ticket that didn't need to exist, which is worse than one missed
callback prompting the user to just ask again - hence the higher precision
bar).

**Known baseline risk:** confirmed during the Sprint 0 out-of-band audit
(see `docs/Sprints.md`) - identical input ("please call me at
0452 111 222") produced inconsistent `check()` results across repeated
runs against `llama3.2:3b`, i.e. non-determinism at the condition-check
step even at `temperature=0`. Expect recall below target on the first
baseline run; this metric exists specifically to turn that anecdotal
finding into a number in production terms (n≈3 manual trials during the
audit vs. a real sample here).

### 4b. Two informational callback figures (added Sprint 2, no target yet)

Recall and precision keep the definitions above. Two figures are reported
alongside them, because those two cannot see certain failures:

- **Phone extraction accuracy**: of the callbacks that started for entries with
  an `expected.extracted_phone`, the share where the number the bot said it would
  call has the same digits as the expected one (formatting ignored, so `0452-111-222`
  matches `0452 111 222`; a different country-code form such as `+61 452...` vs
  `0452...` is reported as a miss and should be read from the detail). A callback to
  the wrong number counts as a recall hit but a miss here, so it is not hidden.
- **Callback false-trigger rate**: of the entries that are not callback requests
  (`callback_false_trigger` and `out_of_scope_question`), the share that started a
  callback anyway.

Note on what precision measures: a negative that contains no 6-digit number is
rejected by the deterministic phone-number pre-check before the language model is
consulted, so it says nothing about the model's own judgment. The three original
false-trigger entries are all of this kind; the Sprint 2 held-out set (`call-021` to
`call-026`) deliberately includes phone numbers so the intent check is exercised.

## 5. Hallucination rate

**What it measures:** does the RAG answer assert something not grounded
in the retrieved chunks for that turn - either inventing facts, or failing
to say "I don't know" when the KB genuinely doesn't cover the question
(`RetrievalNode._SYSTEM_PROMPT` already instructs the model to do this;
this metric checks whether it actually does).

**Formula (v1, manual grading):**
```
hallucinated_answers / total_rag_answers
```
Each `rag-*` golden-set entry lists `expected.retrieval.expected_key_facts`
- short factual claims the answer should be consistent with - or, for
out-of-scope questions (`rag-oos-001`), `expected_source_files: []` with
`expected_behavior` requiring a polite non-answer. Grading v1 is manual
(read the answer, check against the expected facts/behavior) since an
LLM-judge adds its own failure mode on top of an already-small local
model; automating this is a candidate for a later sprint, not Sprint 1.

**Target: ≤5%** (0% is the ideal but not assumed achievable with a 3B
local model on the first pass - this target will be revisited once a real
baseline number exists, per Sprint 1's "every metric has a number, not a
vibe").

## What's deliberately out of scope for Sprint 1

- Automating hallucination grading via an LLM-judge (candidate for a later
  sprint once a manual baseline exists to validate the judge against).
- Retrieval relevance beyond recall@k (e.g. ranking quality/MRR) - recall@k
  is enough to catch the failure modes this system actually has today
  (wrong tier, wrong topic entirely).
- Latency/cost metrics - tracked as raw data by the Sprint 1 structured
  logging, but no target is set here; that belongs to Sprint 7
  (observability).
