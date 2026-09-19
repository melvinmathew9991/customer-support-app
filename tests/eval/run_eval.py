"""Sprint 1 automated eval harness.

Runs every conversation in golden_set.json against the live pipeline
(requires a running Ollama server), scores each one against its `expected`
fields using the structured turn log (logs/turns.jsonl), and prints the
per-entry results plus the aggregate metrics from docs/eval/Metrics.md.

Not a pytest test - like the rest of this project's LLM-dependent behavior
(see the README's Tests section), this is slow and non-deterministic, so
it's run manually rather than in CI. `run_eval.py` doesn't match pytest's
`test_*.py` collection pattern, so it's never picked up by `pytest`.

Usage:
    python tests/eval/run_eval.py
    python tests/eval/run_eval.py --ids ident-001,ident-004
    python tests/eval/run_eval.py --out docs/eval/Baseline-<date>.md
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from customer_support_app.config import get_settings  # noqa: E402
from customer_support_app.logging_config import setup_logging  # noqa: E402
from customer_support_app.pipeline import CustomerSupportPipeline  # noqa: E402

GOLDEN_SET_PATH = PROJECT_ROOT / "tests" / "eval" / "golden_set.json"


def load_golden_set():
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        return json.load(f)


def read_new_log_lines(log_path: Path, start_offset: int):
    """Reads whatever was appended to the turn log since start_offset.

    Conversations run sequentially in this harness (one pipeline instance
    finishes before the next starts), so a simple file-offset window is
    enough to attribute log records to the conversation that produced them
    without needing to thread a conversation id through every log call.
    """
    if not log_path.exists():
        return [], start_offset
    with open(log_path, encoding="utf-8") as f:
        f.seek(start_offset)
        lines = f.readlines()
        new_offset = f.tell()
    records = [json.loads(line) for line in lines if line.strip()]
    return records, new_offset


def run_conversation(entry: dict):
    """Runs one golden-set conversation to completion or to the turn that
    crashes it.

    A turn crashing (e.g. Bug 2 - the missing whisper dependency, hit when
    CallCustomerNode's tool runs) doesn't mean the *node transition* that
    preceded it was wrong: CustomerSupportPipeline._set_current_node sets
    self._current_node before calling the new node's greeting_message(), so
    pipeline._current_node still correctly reflects e.g. CallCustomerNode
    even if greeting_message() then raises. Stopping here (rather than
    letting the exception blow past this function) is what lets the
    category scorer see that real final_node instead of losing it.
    """
    pipeline = CustomerSupportPipeline()
    transcript = []
    error = None
    res, _over = pipeline.run("")
    transcript.append([m.message for m in res])
    for turn in entry["turns"]:
        try:
            res, _over = pipeline.run(turn)
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            break
        transcript.append([m.message for m in res])
    final_node = type(pipeline._current_node).__name__ if pipeline._current_node else None
    return transcript, final_node, error


def _last_assistant_message(transcript):
    for messages in reversed(transcript):
        if messages:
            return messages[-1]
    return None


# --- Per-category scorers. Each returns (passed: bool|None, detail: dict).
# passed=None means "not auto-gradable - see detail for manual review",
# matching docs/eval/Metrics.md #5's v1-manual hallucination grading.


def score_identification(entry, transcript, final_node, _log_records):
    expected = entry["expected"].get("identified_user")
    if expected is None:
        # Some ambiguous_identification entries are deliberately open-ended
        # (see their golden_set.json "notes" - e.g. ident-007's case-sensitive
        # email, ident-010's phone-only lookup gap) and carry an
        # expected_behavior note instead of a fixed identity to score
        # against. Surface what happened for manual review rather than
        # crashing on a KeyError.
        return None, {
            "answer": _last_assistant_message(transcript),
            "final_node": final_node,
            "expected_behavior": entry["expected"].get("expected_behavior"),
            "note": "no fixed expected identity for this entry - manual review",
        }
    last_msg = _last_assistant_message(transcript) or ""
    name_ok = expected["name"] in last_msg
    sub_ok = expected["subscription"].lower() in last_msg.lower()
    node_ok = final_node == entry["expected"].get("final_node", final_node)
    passed = name_ok and sub_ok and node_ok
    return passed, {
        "answer": last_msg,
        "name_ok": name_ok,
        "subscription_ok": sub_ok,
        "node_ok": node_ok,
    }


def score_fails_safe(_entry, _transcript, final_node, _log_records):
    # Must NOT reach AuthenticatedUserNode with a fabricated identity -
    # this is the check that would have caught Bug 1 (see
    # docs/eval/Baseline-2026-09-18.md) before it shipped.
    passed = final_node != "AuthenticatedUserNode"
    return passed, {"final_node": final_node}


def score_retrieval(entry, transcript, _final_node, log_records):
    retrieval_events = [r for r in log_records if r.get("event") == "retrieval"]
    if not retrieval_events:
        return False, {"error": "no retrieval event logged for this conversation"}
    docs = retrieval_events[-1].get("retrieved_docs") or []
    sources = [d["source"] for d in docs if d.get("source")]

    expected_sources = entry["expected"]["retrieval"]["expected_source_files"]
    recall_hit = any(s in sources for s in expected_sources) if expected_sources else True

    expected_tier = entry["expected"].get("tier_used")
    tier_leak = False
    if expected_tier:
        other_tier = "paid" if expected_tier == "free" else "free"
        tier_leak = any(f"assets/{other_tier}/" in s for s in sources)

    passed = recall_hit and not tier_leak
    return passed, {
        "answer": _last_assistant_message(transcript),
        "sources": sources,
        "recall_hit": recall_hit,
        "tier_leak": tier_leak,
    }


def score_out_of_scope(_entry, transcript, final_node, log_records):
    retrieval_events = [r for r in log_records if r.get("event") == "retrieval"]
    sources = retrieval_events[-1].get("retrieved_docs") if retrieval_events else None
    # These questions are never callback requests, so reaching CallCustomerNode
    # is a callback false trigger (auto-gradable), independent of the manual
    # hallucination grading of the answer itself.
    actually_fired = final_node == "CallCustomerNode"
    return (False if actually_fired else None), {
        "answer": _last_assistant_message(transcript),
        "retrieved_docs": sources,
        "actually_fired": actually_fired,
        "final_node": final_node,
        "note": "hallucination grading is manual in v1 - see docs/eval/Metrics.md #5",
    }


# The assistant message that confirms which number the bot will call, in both
# CallCustomerEdge's reply and CallCustomerNode's no-audio-extra reply.
_CALLED_NUMBER_PATTERNS = (
    re.compile(r"calling you now on:\s*(.+)"),
    re.compile(r"callback request for\s*(.+?)\.\s"),
)


def extracted_phone_from(transcript):
    """The number the bot said it would call, or None if it never named one."""
    for messages in transcript:
        for message in messages:
            for pattern in _CALLED_NUMBER_PATTERNS:
                found = pattern.search(message)
                if found:
                    return found.group(1).strip()
    return None


def _digits(text):
    return re.sub(r"\D", "", text or "")


def score_callback(entry, transcript, final_node, _log_records):
    expected_fire = entry["expected"]["callback_expected"]
    actually_fired = final_node == "CallCustomerNode"
    passed = actually_fired == expected_fire
    detail = {"actually_fired": actually_fired, "final_node": final_node}
    # Pass/fail (and so recall and precision) is only about whether the callback
    # started. Extraction accuracy is reported separately: a callback to the wrong
    # number counts as a recall hit but a phone_ok miss. Compared by digits only.
    if expected_fire and actually_fired and "extracted_phone" in entry["expected"]:
        got = extracted_phone_from(transcript)
        detail["extracted_phone"] = got
        detail["phone_ok"] = _digits(got) == _digits(entry["expected"]["extracted_phone"])
    return passed, detail


CATEGORY_SCORERS = {
    "happy_path_identification": score_identification,
    "ambiguous_identification": score_identification,
    "unknown_user_identification": score_fails_safe,
    "subscription_lookup_missing": score_fails_safe,
    "free_tier_question": score_retrieval,
    "paid_tier_question": score_retrieval,
    "adversarial_tier_crossing": score_retrieval,
    "out_of_scope_question": score_out_of_scope,
    "callback_request_explicit": score_callback,
    "callback_request_indirect": score_callback,
    "callback_false_trigger": score_callback,
}

# Which categories feed which docs/eval/Metrics.md metric, for aggregation.
IDENTIFICATION_CATS = {"happy_path_identification", "ambiguous_identification"}
FAILS_SAFE_CATS = {"unknown_user_identification", "subscription_lookup_missing"}
RETRIEVAL_CATS = {"free_tier_question", "paid_tier_question", "adversarial_tier_crossing"}
CALLBACK_RECALL_CATS = {"callback_request_explicit", "callback_request_indirect"}
CALLBACK_ALL_CATS = CALLBACK_RECALL_CATS | {"callback_false_trigger"}


def run_all(golden_set):
    setup_logging()
    settings = get_settings()
    log_path = settings.turn_log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)
    offset = log_path.stat().st_size if log_path.exists() else 0

    results = []
    for entry in golden_set:
        print(f"Running {entry['id']} ({entry['category']})...", file=sys.stderr)
        try:
            transcript, final_node, crash = run_conversation(entry)
            log_records, offset = read_new_log_lines(log_path, offset)
            scorer = CATEGORY_SCORERS.get(entry["category"])
            if scorer is None:
                passed, detail = None, {
                    "error": f"no scorer registered for category '{entry['category']}'"
                }
            else:
                # Score from final_node/log_records as usual even if this
                # conversation crashed partway - a crash after a correct
                # node transition (e.g. Bug 2's whisper crash, which only
                # happens *inside* CallCustomerNode, after CallCustomerEdge
                # already fired correctly) is a different failure than the
                # edge never firing at all, and conflating the two
                # understated callback recall in the 2026-09-19 run.
                passed, detail = scorer(entry, transcript, final_node, log_records)
            if crash:
                detail = dict(detail)
                detail["crash"] = crash
        except Exception as e:
            # A harness-level failure the above couldn't even get a
            # final_node out of (e.g. the very first pipeline.run("") call
            # itself failing) - genuinely unscorable, not just crashed.
            _, offset = read_new_log_lines(log_path, offset)  # resync past any partial output
            passed, detail = False, {"error": f"{type(e).__name__}: {e}"}
        results.append(
            {
                "id": entry["id"],
                "category": entry["category"],
                "passed": passed,
                "detail": detail,
            }
        )
    return results


def compute_metrics(results):
    by_cat = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r)

    def pass_rate(categories):
        entries = [r for cat in categories for r in by_cat.get(cat, [])]
        scored = [r for r in entries if r["passed"] is not None]
        if not scored:
            return None
        return sum(1 for r in scored if r["passed"]) / len(scored), len(scored)

    metrics = {}
    metrics["identification_success_rate"] = pass_rate(IDENTIFICATION_CATS)
    metrics["fails_safe_rate"] = pass_rate(FAILS_SAFE_CATS)
    metrics["retrieval_recall_at_k"] = pass_rate(RETRIEVAL_CATS)

    retrieval_entries = [r for cat in RETRIEVAL_CATS for r in by_cat.get(cat, [])]
    leaked = [r for r in retrieval_entries if r["detail"].get("tier_leak")]
    metrics["tier_leakage_rate"] = (
        (len(leaked) / len(retrieval_entries), len(retrieval_entries))
        if retrieval_entries
        else None
    )

    metrics["callback_recall"] = pass_rate(CALLBACK_RECALL_CATS)
    # Out-of-scope questions are never callback requests, so a fire there is a
    # false trigger and belongs in the precision denominator too.
    callback_all = [
        r for cat in CALLBACK_ALL_CATS | {"out_of_scope_question"} for r in by_cat.get(cat, [])
    ]
    fired = [r for r in callback_all if r["detail"].get("actually_fired")]
    genuine_fired = [r for r in fired if r["category"] in CALLBACK_RECALL_CATS]
    metrics["callback_precision"] = (
        (len(genuine_fired) / len(fired), len(fired)) if fired else None
    )

    # Informational, no target yet: did the bot name the right number, and how
    # often did a message that is not a callback request start one anyway.
    checked = [r for r in callback_all if "phone_ok" in r["detail"]]
    metrics["phone_extraction_accuracy"] = (
        (sum(1 for r in checked if r["detail"]["phone_ok"]) / len(checked), len(checked))
        if checked
        else None
    )
    negatives = [r for r in callback_all if r["category"] not in CALLBACK_RECALL_CATS]
    false_fired = [r for r in negatives if r["detail"].get("actually_fired")]
    metrics["callback_false_trigger_rate"] = (
        (len(false_fired) / len(negatives), len(negatives)) if negatives else None
    )

    return metrics


def build_report(results, metrics):
    lines = ["# Eval run results\n", "| id | category | result |", "|---|---|---|"]
    for r in results:
        status = (
            "PASS"
            if r["passed"] is True
            else ("FAIL" if r["passed"] is False else "MANUAL REVIEW")
        )
        lines.append(f"| {r['id']} | {r['category']} | {status} |")

    lines.append("\n## Aggregate metrics (docs/eval/Metrics.md)\n")

    def fmt(name, target, value):
        if value is None:
            return f"- **{name}**: no scored cases (target: {target})"
        rate, n = value
        return f"- **{name}**: {rate:.0%} (n={n}) — target: {target}"

    lines.append(
        fmt(
            "Identification success rate",
            "≥95% clean / ≥80% ambiguous",
            metrics["identification_success_rate"],
        )
    )
    lines.append(fmt("Fails-safe rate", "100%", metrics["fails_safe_rate"]))
    lines.append(fmt("Retrieval recall@k", "≥90%", metrics["retrieval_recall_at_k"]))
    lines.append(fmt("Tier-leakage rate", "0%", metrics["tier_leakage_rate"]))
    lines.append(fmt("Callback recall", "≥90%", metrics["callback_recall"]))
    lines.append(fmt("Callback precision", "≥95%", metrics["callback_precision"]))
    lines.append(
        fmt("Phone extraction accuracy", "no target yet", metrics["phone_extraction_accuracy"])
    )
    lines.append(
        fmt("Callback false-trigger rate", "no target yet", metrics["callback_false_trigger_rate"])
    )
    n_crashed = sum(1 for r in results if "crash" in r["detail"])
    if n_crashed:
        lines.append(
            f"  - Note: {n_crashed} entries hit a crash after their node transition "
            "was already scored (see each entry's `crash` field below) - callback "
            "recall/precision reflect whether CallCustomerEdge *fired* correctly, "
            "not whether the ticket-creation flow completed end-to-end. A crash "
            "there is a separate, already-tracked issue (Bug 2)."
        )
    lines.append(
        "- **Hallucination rate**: not auto-scored in v1 (manual grading by design "
        "— see docs/eval/Metrics.md #5). Review the `out_of_scope_question` and "
        "`adversarial_tier_crossing` entries' answers below by hand."
    )

    lines.append("\n## Per-entry detail\n")
    for r in results:
        lines.append(f"### {r['id']} ({r['category']})")
        lines.append(f"```json\n{json.dumps(r['detail'], indent=2)}\n```\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", help="comma-separated golden-set ids to run (default: all)")
    parser.add_argument("--out", help="write the report to this path instead of stdout")
    args = parser.parse_args()

    # Windows consoles often default to a non-UTF-8 codepage (cp1252),
    # which chokes on this report's >=/em-dash characters.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    golden_set = load_golden_set()
    if args.ids:
        wanted = set(args.ids.split(","))
        golden_set = [e for e in golden_set if e["id"] in wanted]

    results = run_all(golden_set)
    metrics = compute_metrics(results)
    report = build_report(results, metrics)

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Report written to {args.out}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
