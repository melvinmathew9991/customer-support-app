# Larger local model experiment: plan (Sprint 2, #5, #17, #23)

**Written and committed before any run.** Question: are the remaining hallucination
(#5/#17: about 13% on unseen questions vs a 5% target) and callback false triggers
(#23: 83% precision on the held-out cohort vs 95%) limits of the 3B model, or would
a larger local model remove them? Prompt and KB fixes have shown diminishing returns.

## Setup

- Only the model changes: `llama3.2:3b` (baseline) vs `llama3.1:8b` (same family, one
  size up, native tool-calling), selected with `OLLAMA_MODEL`. Same code (`main` at
  `2f878c8`), same KB, same embedding model (no reindex), temperature 0, same golden
  set (122 entries), run through `tests/eval/run_eval.py`.
- The 3B numbers are the existing `Precision-FullEval-2026-09-19.md` (same code).
- Local only: no API key, no KB text leaves the machine. OpenAI is not tested.

## What is measured, and the criteria (fixed now)

1. **Callback, held-out cohort `call-037` to `call-058`** (12 negatives, 10 positives),
   through the full pipeline. Target: precision >=95% (with 10 positives that means
   zero false triggers) and recall >=90%. Secondary, model only: the intent check with
   the previous and the current wording and no deterministic patterns, for both
   models, to see the model's own judgment.
2. **Hallucination** on the 51 answered `rag-*` entries (14 free, 14 paid, 11
   adversarial, 12 out of scope). Hand-graded against the KB text as correct /
   borderline / hallucinated, by one reader, **blind to which model wrote each
   answer** (labels shuffled; identical answers get one verdict). Target <=5%.
   Threshold for "meaningfully better": at least **3 fewer hallucinated answers**
   than 3B (one answer is about 2 points, so 1 or 2 is noise).
3. **No regression** in the machine-scored metrics: identification 100%, fails-safe
   100%, retrieval recall >=90% (currently 100%), tier leakage 0%, phone extraction.
4. **Identity tool over-calling:** the earlier ablation (8 non-identifying messages,
   original tool description), for both models: how often the tool is called with an
   invented value, and whether the existing guard still rejects it.
5. **Cost:** wall-clock time for the full eval per model.

**Decision rule.** The 8B is worth recommending as an option only if (1) precision
>=95% and recall >=90% AND (2) at least 3 fewer hallucinated answers AND (3) no
regression. Otherwise the report says it is not sufficient. Whether the project's
default should move off a small local model is the maintainer's decision either way.

## Caveats stated in advance

- One run per model (the 3B pipeline was identical across 3 repeat runs at
  temperature 0; the 8B is assumed the same and spot-checked).
- One reader grades hallucination. Blinding removes model bias, not reader error.
- The prompts, guards and intent patterns were developed around 3B behavior, which
  favors the 3B. The cohort's negatives were written knowing earlier failure shapes.
- A larger model is slower and heavier; that cost is part of the answer.
