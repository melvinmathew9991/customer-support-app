# Held-out callback results (Sprint 2, issue #8)

Callback recall of 100% (n=7) had been measured on the set the fix was developed
against, and reading that set showed the precision figure was not informative
either. This adds 16 entries written from scratch and committed (`dc204dd`, 12:44)
**before any run**, extends the scorer to check which number the bot says it will
call (`1bd7fb9`, 12:47), then runs all 26 callback entries once. Raw report:
`Callback-HeldOut-2026-09-19.md`. No crashes.

## Results (26 entries: 10 existing + 16 new)

| Metric | Result | Target |
|---|---|---|
| Callback recall | **100%** (17/17); new positives 10/10 | >=90%, met |
| Callback precision | **85%** (17 of the 20 callbacks that started were genuine) | >=95%, **not met** |
| Phone extraction accuracy (new, informational) | **94%** (16/17) | none yet |
| Callback false-trigger rate (new, informational) | 33% (3 of 9 non-callback entries) | none yet |

### Recall holds on unseen phrasing

All 10 new positives started a callback: international `+61` and US `+1` formats,
dash-separated, unspaced, a bracketed landline, the number stated first, a terse
lowercase request, formal ("telephone me"), a scheduling ask, a stated preference,
and a request with trailing context. All 10 also named the right number.

### Precision does not

3 of the 6 new negatives started a callback:

| Entry | Message | Result |
|---|---|---|
| `call-023` | "Is 1800 555 010 the right number to reach your support team by phone?" | **false trigger** |
| `call-025` | "I changed my phone number, it's 0452 700 812 now. Can you update my profile?" | **false trigger** |
| `call-026` | "Does the store support text message alerts to +61 452 000 111 for new orders?" | **false trigger** |
| `call-021` | "Please email me instead, don't call. My old number was 0452 909 120." | correctly ignored |
| `call-022` | "My order number is 20481937, where is it?" | correctly ignored |
| `call-024` | "I called 0452 314 559 yesterday and nobody answered, is that line working?" | correctly ignored |

The three failures share a shape: a phone number plus phone-related context, but
no request to be called.

**Why the headline numbers understate this.** The phone-number pre-check rejects
any message without a 6-digit number before the model is consulted. All three
original false-trigger entries (`call-003`, `-009`, `-010`) contain no digits, so
they can never fail: they said nothing about the model's judgment, and Sprint 1's
"100% precision" was uninformative. On the negatives the model actually judged
(all six new ones), the false-trigger rate is **3/6 = 50%**. The blended 33%
(3/9) is diluted by the three that cannot fail; the 85% precision is diluted the
same way, by the 17 genuine callbacks.

### A wrong number, hidden until now

`call-007` (existing entry, `michaeljackson@gmail.com`) says "Is it possible for
an agent to reach out to me by phone? **0452 222 111**", and the bot answered that
it was calling **0452 333 666**. That is the phone number on Michael Jackson's
profile, not the one he typed. The callback started, so the old scorer counted it
as a pass; the entry passed for the whole of Sprint 1 while calling the wrong
number. Extraction accuracy is 16/17 only because of this one.

Likely cause (not confirmed): the extraction step sees the whole message history,
including the internal `system: User Info retrieved: ... phone=...` line. That is
the same leak that biased the intent check (fixed in Sprint 1 for `check()` only).
It matches an earlier observation where an out-of-scope question that falsely
triggered a callback named the profile number.

## What this changes

- **Callback precision is not at target** (85% vs >=95%), and the real weakness is
  the model's judgment when a phone number is present in a non-request.
- **A callback can go to a number the user did not give.** Recall and precision
  cannot show this; the new extraction figure can.
- **The deterministic pre-check is doing most of the work.** It removes every
  negative without a long number, so the model is only decisive on messages that
  contain one, and there it is unreliable.

## Not fixed here

This is a measurement change. The set is now a used one: fixes need a fresh
cohort. Candidate fixes to test next:
- Extraction: feed the extraction step only user/assistant messages (as `check()`
  does), and add a deterministic guard that the extracted number's digits appear in
  the user's own message, mirroring the identification lookup guard. Fallback:
  refuse to start the callback and ask for the number.
- Intent: tighten the condition for numbers offered for another purpose, or require
  a call word near the number. Any rewording risks the recall-for-precision trade
  seen in Sprint 1, so it needs the held-out set to check.

## Caveats

- 26 entries, one run of a non-deterministic 3B model; 3 false triggers out of 6 is
  a small sample.
- The negatives were written knowing how the guard and the intent condition work.
- Extraction is compared by digits; a country-code variant (`+61 452...` for
  `0452...`) would count as a miss. None occurred.
- The no-number phrasing ("please call me") is excluded until the callback-behavior
  decision (#7).
