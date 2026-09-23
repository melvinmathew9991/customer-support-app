# Notice: the files under `assets/`

Everything in this directory is original, synthetic sample data written for this project
(issue #14, 2026-09-23). It is covered by the project's `LICENSE` (MIT), like the code.

## What is here

| Path | What it is | Origin |
|---|---|---|
| `free/*.txt`, `paid/*.txt` | The knowledge base for **Brightstall**, a fictional online store platform: compliance, locations, payments and point of sale, one file per topic per tier | Written for this project. Brightstall, Brightstall Payments, Brightstall POS, Pay in Parts and the lending partner Crestline Credit are invented names. The designated-agent address is fictional and uses the reserved `.example` domain. The knowledge base describes the DMCA notice-and-counter-notice process, which is US law, not anyone's help-center text |
| `audio/customer_support_call.txt` | The script of a sample support call between an agent ("Ruby") and a customer ("Michael") about a point-of-sale plan problem | Written for this project. Both people are fictional, and the call contains no personal details |
| `audio/customer_support.wav` | That script, spoken | Synthesized from the script with the Windows speech engine by `scripts/generate_sample_call.ps1` (voices "Microsoft Zira Desktop" and "Microsoft David Desktop") |

## History

Until 2026-09-23 this directory held third-party sample data whose origin was never
recorded: knowledge-base text that read as Shopify help-center content, and a recorded
call whose source was unknown. It was replaced rather than documented because its terms
could not be confirmed. The replacement keeps the same files, tiers and tested facts
(the free-tier limits on locations, in-person selling and manual payments; the
compliance deadlines and notice contents), so the golden set still applies.

The old files remain in git history (commits before the #14 replacement). Removing them
from the current tree does not remove them from history. The legacy prototype
`notebooks/customer_support.ipynb` still contains the old greeting copy and one saved
model answer that paraphrases the old text; it is kept unchanged as a record of the
prototype.

## Changing it

The code runs on any text you put in `assets/free/` and `assets/paid/`. Changing the
knowledge base changes the evaluation results: rebuild the index
(`python scripts/reindex_kb.py`), re-run the golden set (`tests/eval/run_eval.py`), and
see `README.md`, "Updating the knowledge base". To change the sample call, edit the
script and re-run `scripts/generate_sample_call.ps1`.
