# Run-to-run variance of the golden-set eval: results (2026-09-21 to 22)

Follows `Variance-Plan-2026-09-21.md`, whose reading rules were committed before any run.
Five full runs of the 135-entry golden set on unchanged `main` (`8d450ae`), `llama3.2:3b`.
Raw reports: `docs/eval/variance/run-1.md` .. `run-5.md`. Summary produced by
`scripts/summarize_eval_runs.py docs/eval/variance/run-*.md`.

## Result in one paragraph

**No run-to-run variance in any scored metric, at n=5 on this machine.** All eight aggregate
metrics were identical in all five runs, and no entry changed result. The only difference
between runs was the wording of one answer (`rag-free-008`), which came from the model
server and not from retrieval or this project's code. That does **not** explain the earlier
100% vs 97% callback recall difference, which was a single entry (`call-031`) failing once;
five clean runs neither reproduce it nor rule it out (see below).

## Runs

| Run | Started | Wall time | Exit |
|---|---|---|---|
| 1 (cold model) | 2026-09-21 23:13:42 | 796 s | 0 |
| 2 | 23:26:58 | 788 s | 0 |
| 3 | 23:40:07 | 783 s | 0 |
| 4 | 23:53:10 | 786 s | 0 |
| 5 | 2026-09-22 00:06:16 | 787 s | 0 |

Wall time is steady (783-796 s). The cold model load in run 1 cost about 8 to 13 seconds.

## 1. Aggregate metrics: spread is 0.0 pp for every metric

| Metric | Every run | Spread (pp) |
|---|---|---|
| Identification success | 8/8 (100%) | 0.0 |
| Fails-safe | 6/6 (100%) | 0.0 |
| Retrieval recall@k | 39/39 (100%) | 0.0 |
| Tier leakage | 0/39 (0%) | 0.0 |
| Callback recall | 44/44 (100%) | 0.0 |
| Callback precision | 44/47 (93.6%) | 0.0 |
| Phone extraction | 44/44 (100%) | 0.0 |
| Callback false-trigger rate | 3/38 (7.9%) | 0.0 |

Entry results were 120 PASS, 3 FAIL, 12 MANUAL REVIEW in every run. The three failures are the
same each time: `call-042` and `call-047` (held-out false triggers, #23) and `call-070` (the
one trade-off of the #33 fix). These numbers also equal `Post-Sprint3-FullEval-2026-09-21.md`,
the last full run before this one.

## 2. Flippers: 0 of 135

No entry changed PASS / FAIL / MANUAL REVIEW between runs. No metric moved by even one entry, so
none is "materially noisy" by the plan's rule.

## 3. Text-variant entries: 1 of 135 (`rag-free-008`)

Every other entry's detail block (answer text, routing decision, extracted numbers) was
byte-identical across all five runs. That includes the 12 MANUAL REVIEW entries, so the
answers behind the hand-graded hallucination figure did not change between these runs.

`rag-free-008` ("What's the difference between a copyright and a trademark?") gave one answer
in run 1 (186 characters) and another in runs 2-5 (327 characters, identical to each other).
Both state the copyright/trademark difference; the longer one adds trade dress. Neither was
graded here.

**Attribution (post-hoc, not part of the plan):**
- The RAG prompt is the system prompt, the user's question and the retrieved chunks:
  `chain.invoke({"input": last_user_message})` in `RetrievalNode._predict`. It carries no
  conversation history, so the random greeting and retry wording in `agents/support.py`
  (`random.choice`) cannot reach it.
- Retrieval was the same every time: the last 8 turn-log records for this question hold
  the same four chunks with identical scores.
- So the model saw the same input and produced different text at `temperature=0`. That is
  non-determinism in generation on the model server, not in this project's code.

Limits of that reading: the retrieval comparison comes from the logging lookup
(`similarity_search_with_score`), not the chain's own retriever call, which uses the same
index and query but was not captured; and the model's exact prompt was not recorded.

## 4. The earlier 100% vs 97% difference

The two runs were `Precision-FullEval-2026-09-19.md` (callback recall 36/37, precision n=38)
and `Model-Full-llama3-2-3b-2026-09-19.md` (37/37, n=39). The reports differ on one entry:
**`call-031`** ("I'd rather talk this through by phone. My number is 0421 907 366.") was FAIL in
the first and PASS in the second.

- **Same code:** no commit touching `src/` lies between the two reports' commits
  (`git log 4a23125..efe393b -- src` is empty).
- **A model-decided entry:** `call-031` matches none of the deterministic call-me patterns
  (`_CALL_ME_RE` needs "call me", "give me a call" and similar), so the intent check that
  decides it is the model. That is where a flip can happen, and it is not a case the
  patterns pin down.
- **Record for this entry** across the eleven full 3B runs that contain it (the 8B run is a
  different model and excluded): FAIL once (`Precision-FullEval-2026-09-19`), PASS in the ten
  others (`Model-Full-llama3-2-3b`, the two Sprint 2 audit runs, `Sprint3-Persistence`,
  `Post-Sprint3`, and runs 1-5 here). The code changed across those runs (audit fixes, #37,
  #33, Sprint 3), so this is a tally, not a clean rate.
- **Five clean runs do not settle it.** If `call-031` failed 10% of the time, five runs would
  all pass about 59% of the time (0.9^5). What caused the one failure is unknown; Ollama's state
  before the run is a guess and was not tested.

## 5. What this means

- **Observed noise floor, over these 5 runs:** 0 pp on every aggregate metric. Expect an
  occasional one-entry difference all the same, because it happened once in the record: a 3B
  intent check at `temperature=0` is not guaranteed to repeat on a borderline phrase.
- **For Sprint 5's gate (a suggestion, not a measurement):** a metric threshold alone is the
  wrong tool. A tolerance of one entry would absorb a flip like `call-031`'s, but it would
  also have let through the one-entry cost of the #33 fix (`call-070`), and a zero tolerance
  would fail on the flip. What separates the two is a re-run: flag any entry whose result
  changed against the last accepted run, re-run just those entries several times, and fail
  only if the change reproduces. A flip that does not reproduce is noise; `call-070` did
  reproduce. Wording differences like `rag-free-008` change no score and must not fail a gate.
- **Before-and-after claims:** a one-entry change on a model-decided entry is inside what has
  been observed, so on its own it is not evidence either way. Re-run that entry several times
  before calling it a regression or an improvement.

## Limits

- Five runs, one machine, one model, one night. A rarer flip than about 1 in 5 runs per entry
  would usually not appear, so "0 flippers" is a lower bound on the true range.
- Not tested: Phase 2 of the plan (skipped, as it says, because no entry flipped); whether the
  random wording in the callback path can move `call-031`'s intent check (it can reach that
  prompt, unlike the RAG prompt); whether Ollama's warm or cold state matters (runs 2-5 were
  warm, and run 1 matched them); another GPU load or a different day.
- The hand-graded hallucination set was not re-graded. Only whether its answers changed was
  observed, and they did not.
- Run order was fixed, so an order effect cannot be separated from noise.

## Reproduce

```bash
# five full runs, then the comparison
for i in 1 2 3 4 5; do python tests/eval/run_eval.py --out docs/eval/variance/run-$i.md; done
python scripts/summarize_eval_runs.py docs/eval/variance/run-*.md
```
