"""Deterministic checks of the CI regression gate's comparison logic (no LLM, no Ollama).

docs/Eval-Gate-Design.md has the design; scripts/eval_gate.py is what this tests.
"""
import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "eval_gate", _ROOT / "scripts" / "eval_gate.py"
)
eval_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eval_gate)


def _result(entry_id, passed, category="happy_path_identification"):
    return {"id": entry_id, "category": category, "passed": passed, "detail": {}}


def _baseline(entries):
    return {"manifest": {"git_sha": "deadbeef", "model": "ollama:test"}, "entries": entries}


def test_a_clean_rerun_flags_nothing():
    results = [_result("a", True), _result("b", False), _result("c", None)]
    baseline = _baseline({"a": True, "b": False, "c": None})
    assert eval_gate.check_regressions(results, baseline) == []


def test_true_to_false_is_a_regression():
    results = [_result("a", False)]
    baseline = _baseline({"a": True})
    failures = eval_gate.check_regressions(results, baseline)
    assert len(failures) == 1
    assert "a" in failures[0]
    assert "True" in failures[0]


def test_none_to_false_is_a_regression():
    # e.g. rag-oos-001: used to stay silent/manual, now falsely fires a callback.
    results = [_result("rag-oos-001", False, category="out_of_scope_question")]
    baseline = _baseline({"rag-oos-001": None})
    failures = eval_gate.check_regressions(results, baseline)
    assert len(failures) == 1
    assert "rag-oos-001" in failures[0]


def test_already_false_is_not_a_new_regression():
    results = [_result("a", False)]
    baseline = _baseline({"a": False})
    assert eval_gate.check_regressions(results, baseline) == []


def test_false_to_true_is_not_a_regression():
    # An improvement, or noise - either way, not what this gate is for.
    results = [_result("a", True)]
    baseline = _baseline({"a": False})
    assert eval_gate.check_regressions(results, baseline) == []


def test_missing_baseline_entry_is_still_caught_if_now_failing():
    results = [_result("new-entry", False)]
    baseline = _baseline({})
    failures = eval_gate.check_regressions(results, baseline)
    assert len(failures) == 1
    assert "no baseline entry" in failures[0]


def test_missing_baseline_entry_that_passes_is_not_flagged():
    results = [_result("new-entry", True)]
    baseline = _baseline({})
    assert eval_gate.check_regressions(results, baseline) == []


def test_build_baseline_records_entries_and_a_manifest():
    results = [_result("a", True), _result("b", False)]
    baseline = eval_gate.build_baseline(results)
    assert baseline["entries"] == {"a": True, "b": False}
    assert "git_sha" in baseline["manifest"]
    assert "model" in baseline["manifest"]
    assert "generated_at" in baseline["manifest"]


def test_load_smoke_entries_exits_on_an_id_not_in_the_golden_set(monkeypatch):
    monkeypatch.setattr(eval_gate, "SMOKE_IDS", ["not-a-real-id"])
    try:
        eval_gate.load_smoke_entries()
        assert False, "expected SystemExit"
    except SystemExit as error:
        assert "not-a-real-id" in str(error)


def test_every_smoke_id_exists_in_the_current_golden_set():
    # Guards against the golden set being restructured out from under the gate.
    entries = eval_gate.load_smoke_entries()
    assert {e["id"] for e in entries} == set(eval_gate.SMOKE_IDS)
