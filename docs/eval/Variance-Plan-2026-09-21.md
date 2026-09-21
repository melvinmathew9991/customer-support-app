# Run-to-run variance of the golden-set eval: plan (2026-09-21)

Written and committed **before any run**, like the other plans in this directory, so the
reading rules cannot be bent to fit the numbers.

## Question

`docs/Sprints.md` carries an unexplained item from Sprint 2: a fresh full run of the 3B
on the same code differed slightly from the earlier full run (callback recall 100% vs
97%), and it was "not investigated". How much does the eval move between runs of
unchanged code, and where does the movement come from?

This matters beyond the curiosity. Sprint 5 plans a CI gate that fails on a regression;
a gate tighter than the noise fails on nothing, and one looser than it misses real
regressions. The claims in every report so far (single runs, small n) also depend on it.

## What is held fixed

| | |
|---|---|
| Code | `main` at `8d450ae` (merge of #48), nothing changed on the branch except this plan and, later, the results |
| Model | `llama3.2:3b` (digest `a80c4f17acd5`), embeddings `nomic-embed-text` (digest `0a109f422b47`), Ollama 0.34.2 |
| Sampling | as shipped: `temperature=0`, no seed, `num_predict` 1024 (`LLM_MAX_TOKENS`), 120 s call timeout (`LLM_TIMEOUT_SECONDS`), both the defaults (no `.env` override) |
| Knowledge base | unchanged; `scripts/reindex_kb.py --check` reports free 14/14 and paid 15/15, none stale |
| Golden set | all 135 entries, in file order, one conversation at a time |
| Machine | the maintainer's Windows laptop, RTX 4060 8 GB (319 MiB in use before the first run), project `.venv`, nothing else deliberately running |

## Phase 1: five full runs

Run the full golden set **5 times, back to back**, into `docs/eval/variance/run-1.md` ..
`run-5.md`, using `python tests/eval/run_eval.py --out ...` unmodified. Run 1 also loads
the model from cold, so it is kept and its wall time is reported separately.

Per run the harness gives, per entry, PASS / FAIL / MANUAL REVIEW and a detail block (the
answer text for answered questions, the routing decision and numbers for callbacks).

### What will be computed

1. **Each aggregate metric per run**, then min, max, mean and spread (max - min, in
   percentage points) across the five.
2. **Flippers:** entries whose PASS/FAIL result is not the same in all five runs.
3. **Text-variant entries:** entries whose detail block (the answer text or extracted
   values) is not byte-identical across the five runs, whether or not the result changed.
   This is a more sensitive measure than pass/fail, and the only one that sees the
   hand-graded hallucination entries.
4. Wall time per run.

### How the results will be read (fixed now)

- **No flippers and identical aggregates:** report "no run-to-run variance measured at n=5
  on this machine". That does not explain the earlier 100% vs 97% difference; say so, and
  list what else differed between those two runs from the audit reports.
- **Aggregates differ or there are flippers:** the observed spread per metric is the noise
  floor for that metric. A CI gate or a before/after claim must exceed it. State it as
  "observed over 5 runs", never as a bound: five runs cannot show that a rarer flip does
  not exist.
- **Any metric that moves by more than one entry** (its numerator changes by 2 or more
  between two runs) is called out as materially noisy.
- Entries are described by name only for flippers; no entry is re-labelled, and nothing is
  re-graded by hand.

## Phase 2: only if Phase 1 finds flippers

Attribute the movement, on the flipping entries only (`--ids`), 10 runs each:

- **A. As shipped**, to estimate each flipper's own pass probability.
- **B. With the code's own randomness pinned:** `GreetingNode`/`CallCustomerNode` pick
  their wording with `random.choice` (`agents/support.py`), so the assistant text the model
  sees in later turns differs between runs by design. Pin the choice to the first option
  through a throwaway wrapper (no change to `src/`), then repeat.

If B is stable and A is not, the variance is ours (wording that reaches the model). If B
flips as often as A, it is the model server (sampling or batching non-determinism at
`temperature=0`). If neither flips, the Phase 1 flips did not reproduce, and that is
reported as such.

Phase 2 is skipped, and this file says so, if Phase 1 shows no flippers.

## Limits, stated up front

- Five runs on one machine, one model, one day. Rare flips will be missed and the spread is
  a lower bound on the true range, not an estimate of its width.
- The hand-graded hallucination set is not re-graded; only whether its answers change is
  observed.
- A run does not carry state between conversations, but the model server does (loaded
  model, prompt cache); run order is fixed, so an order effect cannot be separated from
  noise here.
- If Ollama, the model or the machine changes, these numbers do not carry over.
