from langchain_core.exceptions import OutputParserException

from customer_support_app.graph.edge import BaseEdge


class FlakyEdge(BaseEdge):
    """A BaseEdge whose _parse() outcome is scripted call-by-call, so the
    retry-counter bookkeeping in BaseEdge.execute() can be exercised
    deterministically without any LLM involved."""

    def __init__(self, outcomes, max_retries=3):
        super().__init__(model=None, max_retries=max_retries)
        self._outcomes = iter(outcomes)

    def _get_message_output(self, msg_input):
        return None

    def check(self, model_output):
        return True

    def _parse(self, model_input):
        if next(self._outcomes):
            return "ok"
        raise OutputParserException("simulated failure")


def test_num_fails_accumulates_across_consecutive_failures_and_only_resets_on_success():
    """Regression test: _num_fails used to be reset to 0 at the start of every
    execute() call (even before the attempt), so it could never reach
    max_retries. It must now only reset on a successful parse."""
    edge = FlakyEdge(outcomes=[False, False, False, True, False], max_retries=3)

    first = edge.execute(None)
    assert first.should_continue is False
    assert first.num_fails == 1

    second = edge.execute(None)
    assert second.should_continue is False
    assert second.num_fails == 2

    # third consecutive failure hits max_retries -> edge gives up and lets the
    # conversation continue anyway rather than looping forever
    third = edge.execute(None)
    assert third.should_continue is True
    assert third.num_fails == 3

    # a success resets the counter back to 0
    fourth = edge.execute(None)
    assert fourth.should_continue is True
    assert fourth.num_fails == 0

    # a fresh failure right after a success must NOT immediately hit
    # max_retries - it starts counting from 0 again
    fifth = edge.execute(None)
    assert fifth.should_continue is False
    assert fifth.num_fails == 1


def test_successful_parse_returns_the_parsed_result():
    edge = FlakyEdge(outcomes=[True])

    output = edge.execute(None)

    assert output.should_continue is True
    assert output.result == "ok"
