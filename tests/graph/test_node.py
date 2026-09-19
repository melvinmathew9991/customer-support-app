from langchain_core.exceptions import OutputParserException

from customer_support_app.graph.edge import BaseEdge
from customer_support_app.graph.node import BaseNode


class FakeEdge(BaseEdge):
    """A minimal concrete BaseEdge whose success/failure is controlled directly,
    for exercising BaseNode without any LLM involved."""

    def __init__(self, should_succeed: bool, out_node=None, result="fake-result"):
        super().__init__(model=None, max_retries=3, out_node=out_node)
        self._should_succeed = should_succeed
        self._result = result

    def _get_message_output(self, msg_input):
        return None

    def check(self, model_output):
        return True

    def _parse(self, model_input):
        if self._should_succeed:
            return self._result
        raise OutputParserException("simulated failure")


class FakeNode(BaseNode):
    def __init__(self, edges=None, final_state=False):
        super().__init__(edges=edges, final_state=final_state)
        self.no_edges_found_called_with = None

    def greeting_message(self):
        return "greeting"

    def no_edges_found(self, user_input):
        self.no_edges_found_called_with = user_input
        return "fallback"


def test_run_to_continue_returns_first_succeeding_edge():
    failing = FakeEdge(should_succeed=False)
    succeeding = FakeEdge(should_succeed=True, result="picked-me")
    node = FakeNode(edges=[failing, succeeding])

    result = node.run_to_continue("input")

    assert result.should_continue is True
    assert result.result == "picked-me"


def test_run_to_continue_returns_none_result_when_no_edges():
    node = FakeNode(edges=[])

    assert node.run_to_continue("input") is None


def test_execute_falls_back_to_no_edges_found_when_all_edges_fail():
    node = FakeNode(edges=[FakeEdge(should_succeed=False), FakeEdge(should_succeed=False)])

    result = node.execute("some input")

    assert result == "fallback"
    assert node.no_edges_found_called_with == "some input"


def test_execute_sets_node_input_on_next_node_when_an_edge_succeeds():
    downstream = FakeNode(edges=[])
    succeeding = FakeEdge(should_succeed=True, out_node=downstream, result="payload")
    node = FakeNode(edges=[succeeding])

    node.execute("input")

    assert downstream._node_input == "payload"


def test_is_node_final_reflects_constructor_flag():
    assert FakeNode(edges=[], final_state=True).is_node_final() is True
    assert FakeNode(edges=[], final_state=False).is_node_final() is False
