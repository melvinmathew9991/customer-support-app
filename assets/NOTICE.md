# Notice: the files under `assets/`

The project's `LICENSE` (MIT) does **not** cover anything in this directory. These
files are sample data used to run and test the agent, and their origin and terms
have not been confirmed. This is a record of what is known, not a grant of rights.

## What is here

| Path | What it is | What is known about its origin |
|---|---|---|
| `free/compliance.txt`, `paid/compliance.txt` | Knowledge-base text on platform compliance; the two files are byte-identical | Reads as Shopify help-center text ("At Shopify, we believe in making commerce better for everyone", 39 mentions of Shopify). Unchanged since the initial commit |
| `free/payments.txt`, `paid/payments.txt` | Knowledge-base text on payment methods | Reads as Shopify help-center text. `paid/payments.txt` is unchanged since the initial commit; one line of `free/payments.txt` was rewritten in Sprint 2 to state the free-tier policy (`d8b0cd0`, #16) |
| `paid/pos.txt` | Knowledge-base text on point of sale | Reads as Shopify help-center text. Unchanged since the initial commit |
| `free/pos.txt`, `free/locations.txt`, `paid/locations.txt` | Knowledge-base text on locations and POS | Adapted from Shopify-style help text and then edited or partly replaced by this project in Sprint 2 to remove tier ambiguities (`docs/eval/KB-Rewrite-Results-2026-09-19.md`). Still describes Shopify features |
| `audio/customer_support.wav` (about 5 MB) | A scripted phone call between an agent ("Ruby", from Shopify) and a customer ("Michael"), used by the optional call-transcription tool | Unknown. The call includes a spoken name, date of birth and email address, presumably fictional; that has not been verified |

All of it arrived in the repository's initial commit (`e8a72b9`, 2026-09-18), and "unchanged"
above means unchanged since then; the initial commit may already differ from any
original. Where each file came from was not recorded at the time and is not
remembered now.

## What this means

- Do not assume you may reuse or redistribute these files. Shopify's help-center
  content and the recording may be subject to their owners' terms.
- The code runs on any text you put in `assets/free/` and `assets/paid/`, so you
  can replace them with your own knowledge base. Changing the KB changes the
  evaluation results: re-run the golden set (`tests/eval/run_eval.py`) and see
  `README.md`, "Updating the knowledge base".
- Removing a file from the current tree does not remove it from git history.

## Open

Tracked in issue #14: confirm the source and terms of each file above, then either
record them here or replace the files with original or synthetic content.
