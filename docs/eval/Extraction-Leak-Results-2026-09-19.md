# Extraction leak fix results (Sprint 2, issue #22)

Issue #22: on `call-007` the callback extraction returned the number on the user's
profile (`0452 333 666`) instead of the one they typed (`0452 222 111`), 5 of 5
runs. This adds 10 entries written before the fix, records a pre-fix baseline,
applies the fix, and re-runs. Reports: `Extraction-Leak-Baseline-2026-09-19.md`
(pre-fix), `Extraction-Leak-PostFix-2026-09-19.md` (fix v1, 11 entries),
`Extraction-Leak-FullEval-guard-only-2026-09-19.md` (fix v1, full set),
`Extraction-Leak-FullEval-2026-09-19.md` (final, full set).

## What changed

1. `PydanticTextBasedEdge._parse` passes only user/assistant messages to the
   extraction model, as `check()` already did (`6702e6f`, 19:41).
2. `CallCustomerEdge._parse` rejects an extracted number whose digits are not in the
   user's own latest message (`6702e6f`).
3. When that guard rejects and the message holds exactly one number, use that number;
   with several, still reject (`783e5e2`, 20:26). Added after the full eval below.

## Fresh cohort (10 entries, committed 19:38 before any run)

Eight requests where the typed number differs from the profile number, plus two
controls where they match (`call-027` to `call-036`). Pre-fix baseline (19:40) vs
fix v1:

| | Pre-fix | Fix v1 |
|---|---|---|
| Fresh entries that started a callback | 9/10 | 9/10 |
| Of those, typed number returned | **9/9** | 9/9 |
| `call-007` (used entry) returns typed number | **no** (profile number) | **yes** |

**The fresh cohort was already at ceiling.** The leak did not reproduce on any of
the 8 new entries, only on `call-007`. So the cohort shows the fix does not regress
extraction; it cannot show the fix improves it. The evidence that it fixes the leak
is `call-007` (a used entry) plus the unit tests, and the guard means the number
called always comes from the user's own message, never from the profile.
`call-033` ("0452 333 999 - please call this number.") did not start a callback
before or after the fix: an intent miss, not a wrong number.

## A regression the full eval caught, and the second change

The full eval after fix v1 (guard only) showed `call-002` no longer starting a
callback (recall 100% to 93%). Stage by stage, 6 of 6 runs: the intent check passed,
then extraction returned `0452255111` for the typed `0452 555 111` (one digit
mis-copied), and the new guard rejected it. Before the fix the model copied this
number correctly, so removing the system line from the prompt exposed a transcription
error on this input. The guard made it a safe failure (no wrong-number call) but the
callback did not start. Change 3 recovers it: the number typed in the message is
used. This change was made after seeing results on a used entry, so the fresh cohort
is the cleaner check of it.

## Full eval (final, 100 entries)

| Metric | Before (`Callback-HeldOut`, 26 callback entries) | Fix v1 (guard only) | Final |
|---|---|---|---|
| Phone extraction accuracy | 94% (16/17) | 100% (25/25) | **100% (26/26)** |
| Callback recall | 100% (17/17) | 93% (25/27) | **96% (26/27)** |
| Callback precision | 85% (17/20) | 89% (25/28) | **90% (26/29)** |
| Identification / fails-safe | not in that run | 100% / 100% | 100% / 100% |
| Retrieval recall / tier leakage | not in that run | 100% / 0% | 100% / 0% |

Recall and precision are not comparable across the columns: the callback set grew
from 17 to 27 positives (the 10 new cohort entries), and the precision gain comes
from those added true positives. The three false triggers (`call-023`, `-025`,
`-026`) are the same as before and unchanged by this fix (tracked in #23).

## Not fixed here

- `call-033` is an intent miss on a positive; see #23 for the callback intent check.
- If a message contains several numbers and extraction is wrong, the callback is
  rejected and the user gets the normal answer, not a prompt asking which number.
- The guard is a digit-substring check, so a truncated copy of the typed number (for
  example without its leading 0) would still pass. None occurred in these runs.
- One run of a non-deterministic 3B model; the counts are small.
