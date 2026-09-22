"""CI regression gate (Sprint 5, docs/Eval-Gate-Design.md).

Runs a small, fixed subset of the golden set against the live pipeline and fails if any
entry that wasn't failing starts failing, compared to the checked-in baseline. The full
135-entry golden set stays a manual pre-merge step (see the PR template) - this only runs
a fast subset, small enough for CI's CPU-only, ephemeral Ollama.

Usage:
    python scripts/eval_gate.py                  # run the gate, exit non-zero on regression
    python scripts/eval_gate.py --update-baseline # regenerate the baseline from a fresh run
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "tests" / "eval"))

from run_eval import compute_metrics, load_golden_set, run_all  # noqa: E402

BASELINE_PATH = PROJECT_ROOT / "tests" / "eval" / "ci_baseline.json"

# One or two entries per golden-set category - broad coverage, small enough to run on
# CI's CPU-only, ephemeral Ollama in a few minutes. Weighted toward tier-leakage
# (adversarial_tier_crossing) and callback, the two historically most fragile areas.
# See docs/Eval-Gate-Design.md for why each one was picked.
SMOKE_IDS = [
    "ident-001",
    "ident-003",
    "ident-004",
    "ident-005",
    "rag-free-001",
    "rag-paid-001",
    "rag-adv-001",
    "rag-adv-002",
    "rag-oos-001",
    "call-001",
    "call-004",
    "call-002",
    "call-003",
    "call-009",
]

# Sentinel so "this id has no baseline entry" is distinguishable from "the baseline's
# verdict for it was None (manual review)" in log messages, even though both are treated
# the same way by the regression rule below.
_NO_BASELINE = object()


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def _model_label() -> str:
    from customer_support_app.config import get_settings

    settings = get_settings()
    if settings.llm_provider == "ollama":
        return f"ollama:{settings.ollama_model}"
    return settings.llm_provider


def load_smoke_entries():
    golden_set = load_golden_set()
    by_id = {e["id"]: e for e in golden_set}
    missing = [i for i in SMOKE_IDS if i not in by_id]
    if missing:
        sys.exit(f"eval_gate: smoke-subset ids missing from golden_set.json: {missing}")
    return [by_id[i] for i in SMOKE_IDS]


def run_smoke():
    results = run_all(load_smoke_entries())
    metrics = compute_metrics(results)
    return results, metrics


def build_baseline(results: list) -> dict:
    return {
        "manifest": {
            "git_sha": _git_sha(),
            "model": _model_label(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "entries": {r["id"]: r["passed"] for r in results},
    }


def check_regressions(results: list, baseline: dict) -> list:
    """A result "regresses" if it wasn't failing in the baseline and is failing now.

    Covers True->False (an obviously passing entry breaks) and None->False (a
    manual-review entry, e.g. out_of_scope_question, starts falsely firing a callback -
    the only way that category can regress in an auto-gradable way). False->False is
    never flagged: an already-known failure isn't a new regression.
    """
    baseline_entries = baseline.get("entries", {})
    failures = []
    for r in results:
        base = baseline_entries.get(r["id"], _NO_BASELINE)
        if base is not False and r["passed"] is False:
            was = "no baseline entry" if base is _NO_BASELINE else f"was {base!r}"
            failures.append(
                f"REGRESSION {r['id']} ({r['category']}): {was}, now False - {r['detail']}"
            )
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="regenerate tests/eval/ci_baseline.json from a fresh smoke run, instead of gating",
    )
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    results, metrics = run_smoke()

    if args.update_baseline:
        baseline = build_baseline(results)
        BASELINE_PATH.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
        print(f"Baseline updated: {BASELINE_PATH}")
        return

    if not BASELINE_PATH.exists():
        sys.exit(f"eval_gate: no baseline at {BASELINE_PATH}. Run with --update-baseline first.")
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    print(
        f"Smoke gate: {len(results)} entries against baseline "
        f"git_sha={baseline['manifest']['git_sha'][:8]} model={baseline['manifest']['model']}"
    )
    for r in results:
        status = "PASS" if r["passed"] else ("FAIL" if r["passed"] is False else "MANUAL")
        print(f"  {status:6} {r['id']} ({r['category']})")

    print("\nAggregate metrics on this subset (context only, not a separate gate):")
    for name, value in metrics.items():
        if value is not None:
            rate, n = value
            print(f"  {name}: {rate:.1%} (n={n})")

    failures = check_regressions(results, baseline)
    if failures:
        print("", file=sys.stderr)
        for line in failures:
            print(line, file=sys.stderr)
        sys.exit(f"\neval_gate: {len(failures)} regression(s) found.")

    print("\neval_gate: no regressions.")


if __name__ == "__main__":
    main()
