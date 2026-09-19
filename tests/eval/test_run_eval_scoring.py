"""Deterministic checks of the callback scoring code in run_eval.py (no LLM, no Ollama)."""
import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("run_eval", _ROOT / "tests" / "eval" / "run_eval.py")
run_eval = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_eval)


def _positive(phone="0452 111 222"):
    return {
        "expected": {
            "callback_expected": True,
            "extracted_phone": phone,
            "final_node": "CallCustomerNode",
        }
    }


NEGATIVE = {"expected": {"callback_expected": False}}
CONFIRM = "Sure we are calling you now on: {}"


@pytest.mark.parametrize(
    "transcript, expected",
    [
        ([["Hi"], [CONFIRM.format("0452 111 222")]], "0452 111 222"),
        ([[CONFIRM.format("+61 452 111 234")]], "+61 452 111 234"),
        (
            [["We've logged your callback request for 0452 111 222. A customer care rep..."]],
            "0452 111 222",
        ),
        ([["Hello"], ["Nothing here"]], None),
    ],
)
def test_extracted_phone_is_read_from_the_confirmation_message(transcript, expected):
    assert run_eval.extracted_phone_from(transcript) == expected


@pytest.mark.parametrize(
    "said, ok",
    [
        ("0452 111 222", True),
        ("0452-111-222", True),  # same digits, different formatting
        ("0452111222", True),
        ("0452 333 666", False),  # a different number, e.g. the one on the user's profile
        ("+61 452 111 222", False),  # different digits (country code), reported as a miss
    ],
)
def test_phone_ok_compares_digits(said, ok):
    passed, detail = run_eval.score_callback(
        _positive(), [[CONFIRM.format(said)]], "CallCustomerNode", []
    )

    assert passed is True  # the callback started, so recall is unaffected
    assert detail["phone_ok"] is ok


def test_wrong_number_still_counts_as_recall():
    passed, detail = run_eval.score_callback(
        _positive(), [[CONFIRM.format("0452 999 999")]], "CallCustomerNode", []
    )

    assert passed is True and detail["phone_ok"] is False


def test_missed_callback_fails_and_has_no_phone_field():
    passed, detail = run_eval.score_callback(
        _positive(), [["An answer"]], "AuthenticatedUserNode", []
    )

    assert passed is False and "phone_ok" not in detail


def test_negatives_are_scored_on_whether_they_fired():
    ok, quiet = run_eval.score_callback(NEGATIVE, [["An answer"]], "AuthenticatedUserNode", [])
    bad, fired = run_eval.score_callback(
        NEGATIVE, [[CONFIRM.format("0452 111 222")]], "CallCustomerNode", []
    )

    assert ok is True and quiet["actually_fired"] is False and "phone_ok" not in quiet
    assert bad is False and fired["actually_fired"] is True


def _result(cat, passed, **detail):
    return {"id": "x", "category": cat, "passed": passed, "detail": detail}


def test_new_metrics_and_unchanged_recall_precision():
    results = [
        _result("callback_request_explicit", True, actually_fired=True, phone_ok=True),
        _result("callback_request_explicit", True, actually_fired=True, phone_ok=False),
        _result("callback_request_indirect", False, actually_fired=False),
        _result("callback_false_trigger", True, actually_fired=False),
        _result("callback_false_trigger", False, actually_fired=True),
        _result("out_of_scope_question", None, actually_fired=False),
    ]

    metrics = run_eval.compute_metrics(results)

    assert metrics["callback_recall"] == (2 / 3, 3)
    assert metrics["callback_precision"] == (2 / 3, 3)  # 3 fired, 2 genuine
    assert metrics["phone_extraction_accuracy"] == (0.5, 2)
    assert metrics["callback_false_trigger_rate"] == (1 / 3, 3)  # 2 false-trigger + 1 oos
    assert "Phone extraction accuracy" in run_eval.build_report(results, metrics)
