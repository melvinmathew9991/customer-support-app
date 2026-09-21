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


SESSION_ENDS = {"expected": {"session_ends": True}}
FAIL_SAFE = "Sorry, we still couldn't verify your account. Please refresh and start again."


def test_a_conversation_that_ends_at_the_fail_safe_message_passes():
    transcript = [["Hi"], ["retry"], ["retry"], [FAIL_SAFE], []]

    passed, _ = run_eval.score_fails_safe(SESSION_ENDS, transcript, "AuthenticatedUserNode", [])

    assert passed is True


def test_an_answer_after_the_fail_safe_message_fails():
    transcript = [["Hi"], ["retry"], ["retry"], [FAIL_SAFE], ["You can accept payments..."]]

    passed, detail = run_eval.score_fails_safe(
        SESSION_ENDS, transcript, "AuthenticatedUserNode", []
    )

    assert passed is False
    assert detail["said_after_fail_safe"] == ["You can accept payments..."]


def test_a_retrieval_after_the_fail_safe_message_fails_even_if_nothing_is_said():
    transcript = [["Hi"], [FAIL_SAFE], []]

    passed, detail = run_eval.score_fails_safe(
        SESSION_ENDS, transcript, "AuthenticatedUserNode", [{"event": "retrieval"}]
    )

    assert passed is False
    assert detail["retrieval_ran"] is True


def test_a_conversation_that_never_reaches_the_fail_safe_message_fails():
    passed, _ = run_eval.score_fails_safe(SESSION_ENDS, [["Hi"], ["retry"]], "GreetingNode", [])

    assert passed is False


def test_the_plain_fails_safe_check_still_only_looks_at_the_final_node():
    entry = {"expected": {}}

    assert run_eval.score_fails_safe(entry, [], "GreetingNode", [])[0] is True
    assert run_eval.score_fails_safe(entry, [], "AuthenticatedUserNode", [])[0] is False


class _ScriptedPipeline:
    """Replies "reply N" to each turn and reports the conversation over after `over_after` turns."""

    over_after = 2

    def __init__(self):
        self.turns = 0
        self._current_node = None

    def run(self, text):
        self.turns += 1
        return [], self.turns >= self.over_after


def test_the_harness_stops_sending_turns_once_the_conversation_is_over(monkeypatch):
    created = []

    def make():
        created.append(_ScriptedPipeline())
        return created[0]

    monkeypatch.setattr(run_eval, "CustomerSupportPipeline", make)

    transcript, _, error = run_eval.run_conversation({"turns": ["a", "b", "c", "d"]})

    assert error is None
    assert created[0].turns == 2  # the greeting run counts as the first turn
    assert len(transcript) == 2
