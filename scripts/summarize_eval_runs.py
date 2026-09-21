"""Compare several golden-set eval reports of the same code, to see run-to-run variance.

Reads reports written by `tests/eval/run_eval.py --out ...`, recomputes the aggregate
metrics from each report's per-entry results with the harness's own `compute_metrics`,
and prints, as Markdown:

  1. each metric per run, with its min, max and spread across runs,
  2. "flippers": entries whose PASS / FAIL / MANUAL REVIEW result is not the same in every run,
  3. "text-variant" entries: entries whose detail block (answer text, routing decision,
     extracted numbers) is not byte-identical in every run, whether or not the result changed.

Usage:
    python scripts/summarize_eval_runs.py docs/eval/variance/run-*.md
"""
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tests" / "eval"))

from run_eval import compute_metrics  # noqa: E402

ROW_RE = re.compile(
    r"^\| (?P<id>\S+) \| (?P<category>\S+) \| (?P<status>PASS|FAIL|MANUAL REVIEW) \|$"
)
DETAIL_RE = re.compile(
    r"^### (?P<id>\S+) \((?P<category>[^)]+)\)\n```json\n(?P<body>.*?)\n```", re.S | re.M
)

METRIC_LABELS = {
    "identification_success_rate": "Identification success",
    "fails_safe_rate": "Fails-safe",
    "retrieval_recall_at_k": "Retrieval recall@k",
    "tier_leakage_rate": "Tier leakage",
    "callback_recall": "Callback recall",
    "callback_precision": "Callback precision",
    "phone_extraction_accuracy": "Phone extraction",
    "callback_false_trigger_rate": "Callback false-trigger rate",
}


def parse_report(path: Path):
    text = path.read_text(encoding="utf-8")
    statuses = {}
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if m:
            statuses[m["id"]] = (m["category"], m["status"])
    details = {m["id"]: m["body"] for m in DETAIL_RE.finditer(text)}
    results = []
    for entry_id, (category, status) in statuses.items():
        passed = True if status == "PASS" else (False if status == "FAIL" else None)
        results.append(
            {
                "id": entry_id,
                "category": category,
                "passed": passed,
                "detail": json.loads(details[entry_id]),
            }
        )
    return results, statuses, details


def main(paths):
    runs = [parse_report(Path(p)) for p in paths]
    names = [Path(p).stem for p in paths]
    ids = list(runs[0][1])
    for name, (_, statuses, _) in zip(names, runs):
        if list(statuses) != ids:
            sys.exit(f"{name}: entry list differs from {names[0]}; not the same golden set")

    print(f"## Aggregate metrics per run ({len(runs)} runs)\n")
    print("| metric | " + " | ".join(names) + " | min | max | spread (pp) | numerator range |")
    print("|---|" + "---|" * (len(names) + 4))
    all_metrics = [compute_metrics(results) for results, _, _ in runs]
    for key, label in METRIC_LABELS.items():
        values = [m[key] for m in all_metrics]
        if any(v is None for v in values):
            continue
        rates = [rate for rate, _ in values]
        ns = {n for _, n in values}
        nums = [round(rate * n) for rate, n in values]
        cells = [f"{num}/{n} ({rate:.1%})" for (rate, n), num in zip(values, nums)]
        denominators = "" if len(ns) == 1 else f" (n varies: {sorted(ns)})"
        print(
            f"| {label} | "
            + " | ".join(cells)
            + f" | {min(rates):.1%} | {max(rates):.1%} | {(max(rates) - min(rates)) * 100:.1f} |"
            f" {min(nums)}-{max(nums)}{denominators} |"
        )

    print("\n## Entry results per run\n")
    print("| result | " + " | ".join(names) + " |")
    print("|---|" + "---|" * len(names))
    for status in ("PASS", "FAIL", "MANUAL REVIEW"):
        counts = [sum(1 for _, s in st.values() if s == status) for _, st, _ in runs]
        print(f"| {status} | " + " | ".join(str(c) for c in counts) + " |")

    flippers = []
    variants = []
    for entry_id in ids:
        statuses = [st[entry_id][1] for _, st, _ in runs]
        bodies = [d[entry_id] for _, _, d in runs]
        if len(set(statuses)) > 1:
            flippers.append((entry_id, runs[0][1][entry_id][0], statuses))
        if len(set(bodies)) > 1:
            variants.append((entry_id, runs[0][1][entry_id][0], len(set(bodies))))

    print(f"\n## Flippers: {len(flippers)} of {len(ids)} entries change result between runs\n")
    if flippers:
        print("| entry | category | " + " | ".join(names) + " |")
        print("|---|---|" + "---|" * len(names))
        for entry_id, category, statuses in flippers:
            print(f"| {entry_id} | {category} | " + " | ".join(statuses) + " |")

    print(
        f"\n## Text-variant entries: {len(variants)} of {len(ids)} have a detail block that is "
        f"not byte-identical in every run\n"
    )
    if variants:
        print("| entry | category | distinct detail blocks across runs |")
        print("|---|---|---|")
        for entry_id, category, distinct in variants:
            print(f"| {entry_id} | {category} | {distinct} |")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1:])
