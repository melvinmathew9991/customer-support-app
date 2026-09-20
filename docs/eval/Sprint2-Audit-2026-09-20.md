# Sprint 2 end-to-end audit (2026-09-20)

An audit of the project as it stood at the end of Sprint 2 (`main` at `9988f40`, the
close-out merge of PR #32), followed by the fixes it led to. Written so the audit can be
re-checked: every claim below names what was run.

## Method

1. **Repository and process:** git history, tags, branches, GitHub issues, milestones, CI
   runs and branch protection, checked with `git` and `gh`.
2. **Report against reality:** every count and metric in `docs/report.md` was recomputed
   from the repo (test count, line counts, golden-set size and categories, issue counts,
   KB index state).
3. **Static checks:** `pytest`, `ruff check` (CI scope and whole repo), `pip check`, a
   search of the tree and of git history for secrets, `Rules.md` compliance by search.
4. **Code read:** `agents/support.py`, `graph/chain_based_node.py`, `tools/rag_responder.py`,
   `tools/user_info_db.py`, `pipeline.py`, `config.py`.
5. **Live re-run:** the golden set on the default `llama3.2:3b`, before the fixes (121 of
   122 entries; `ident-011` skipped because it hangs, #30) and after them (all 122).
   Baseline: `Sprint2-Audit-Baseline-2026-09-20.md`. After:
   `Sprint2-Audit-PostFix-FullEval-2026-09-20.md`.

## What held up

| Check | Result |
|---|---|
| Unit tests | 209 of 209 pass, as reported |
| `ruff check src tests scripts` (the CI gate) | clean |
| CI on the last six merges to `main` | green |
| Branch protection on `main` | pull request and `test` check required, force-push blocked |
| Secrets | none in the tree or in git history; `.env` was never committed; the notebook holds only a placeholder |
| `pip check` | no broken requirements |
| KB index against `assets/` | in sync (free 14, paid 15 chunks, none stale) |
| Report counts | 122 golden entries in 11 categories with unique ids; 1,853 source and 1,068 test lines; 9 open and 7 closed issues; all as reported |
| Sprint 2 definition of done | met (retrieval recall 100%, tier leakage 0%, on 39 entries) |
| Live metrics | reproduced (table below) |

## Findings and what was done

| # | Finding | Disposition |
|---|---|---|
| 1 | README recommended `llama3.1:8b` for flaky flows; the Sprint 2 experiment showed it is worse here | Fixed: README now says to re-run the golden set before switching models |
| 2 | Public repo with no LICENSE; the KB is Shopify-derived (#14) | **Left open by the maintainer's decision**: a legal choice, carried into Sprint 3 |
| 3 | Sprint 2 milestone still open; #29 had no milestone; no `v0.1.0-sprint2` tag although `Git-Workflow.md` requires one | Fixed at close-out: #29, #11 and #30 assigned to Sprint 2; #5, #17, #23 and the new #33 moved to an unscheduled `Known limits` milestone (they are Sprint 2's unmet targets and a related audit finding, not part of any sprint plan; the `Sprint 3` milestone holds only its planned session-persistence scope); Sprint 2 closed and tagged |
| 4 | Stale docs: `tests/eval/README.md` called the golden set a draft; `Phases.md` listed Phase 8 as future work; `report.md` counts were one PR behind | Fixed. Phase 8 is now marked partly done (harness built, CI gate open for Sprint 5) |
| 5 | Callback patterns mishandle negation: `No need to call me back, my number is ...` started a callback; `Never call me before 9am, but do call me on ...` was rejected | First fixed (veto now covers "no need to call"; unit-tested). Second not fixed, tracked as #33: it needs clause-level handling, the overfitting risk already named for #23 |
| 6 | `RetrievalNode._predict` swallowed any exception in the logging-only retrieval lookup, which the eval reads for recall and tier leakage | Fixed: logs a warning with the traceback; unit-tested |
| 7 | The greeting asks for an email or phone number, but the lookup was exact-match on email only, so a phone number could never identify anyone (#11) | Fixed: lookup ignores email case and matches phone by digits; the identity guard compares digits for phone numbers; unit-tested and verified live. `ident-007` and `ident-010` became scored entries |
| 8 | Identification is a lookup, not authentication: anyone who knows an email or phone number is served that customer's tier | Accepted (a PRD non-goal, low-sensitivity KB); recorded under Phase 7 in `Phases.md` |
| 9 | No cap or timeout on LLM calls (#30) | Fixed: `LLM_MAX_TOKENS` (1024) and `LLM_TIMEOUT_SECONDS` (120) apply to both providers, and a timeout becomes a reply instead of a crash. Unit-tested; see the caveat below |
| 10 | Minor: 58 ruff findings in the legacy notebook; 19 files not `ruff format`-clean | Notebook excluded from ruff so `ruff check .` matches the gate. `ruff format` deliberately **not** applied: it is not a gate, and reformatting 19 files would bury history in noise |

## Live results, before and after the fixes (`llama3.2:3b`, single runs)

| Metric | Baseline (121 entries) | After fixes (122 entries) |
|---|---|---|
| Identification success | 100% (n=6) | 100% (n=8: the 6 in the full run, plus `ident-007` and `ident-010`, re-run twice) |
| Fails-safe | 100% (n=4) | 100% (n=5; adds `ident-011`) |
| Retrieval recall@k | 100% (n=39) | 100% (n=39) |
| Tier leakage | 0% (n=39) | 0% (n=39) |
| Callback recall | 100% (n=37) | 100% (n=37) |
| Callback precision | 95% (n=39) | 95% (n=39) |
| Held-out callback cohort precision | 83% (10/12) | 83% (10/12), the same two false triggers (`call-042`, `call-047`) |
| Phone extraction | 100% | 100% |
| Entry results | 105 pass, 2 fail, 14 manual review | 106 pass, 2 fail, 14 manual review |

The only entry-level difference is `ident-011`, which is new to the second run. Nothing
regressed. The two failures are the held-out false triggers already recorded under #23,
not new ones. The 14 manual-review entries are the hand-graded hallucination set; they
were not re-graded here, so the hallucination figure in `docs/report.md` is **not**
independently confirmed.

## Caveats

- **#30 is verified by unit tests, not by a live hang.** `ident-011` completed in the
  post-fix run, but it also completes on some unmodified runs; the hang is intermittent,
  so one pass proves nothing. What is verified is that the settings reach the model and
  that a timeout becomes a reply.
- **Single runs on a 3B model.** The report already notes run-to-run variance; these two
  runs are consistent with it, not a tighter measurement.
- **The two callback checks of finding 5 were probes, not a cohort.** They were not added
  to the golden set, to keep the held-out cohorts untouched; #33 asks for held-out entries
  first.
- **`ident-007` and `ident-010` are regression cases.** They were written before the
  lookup fix and are the entries it was built against.
- **Not checked:** the Streamlit app (last launched in Sprint 1), the OpenAI path (the
  bounds are configured for it and unit-tested, but it has never been exercised), the
  with-whisper path (#10), and the individual eval reports' numbers against raw output.
