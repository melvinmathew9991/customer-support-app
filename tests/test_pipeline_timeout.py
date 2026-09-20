import httpx

from customer_support_app.domain.chat import Role
from customer_support_app.pipeline import TIMEOUT_REPLY, CustomerSupportPipeline


class _SlowNode:
    def __init__(self):
        self.calls = 0

    def execute(self, message_history):
        self.calls += 1
        raise httpx.ReadTimeout("model did not answer")

    def is_node_final(self):
        return False


def test_a_timed_out_model_call_becomes_a_reply_and_the_conversation_carries_on():
    pipeline = CustomerSupportPipeline()
    node = _SlowNode()
    pipeline._current_node = node

    replies, is_over = pipeline.run("what are your payment options?")

    assert [reply.message for reply in replies] == [TIMEOUT_REPLY]
    assert replies[0].role == Role.ASSISTANT
    assert is_over is False
    assert pipeline._current_node is node
    assert pipeline._message_history.messages[-1]["content"] == TIMEOUT_REPLY

    pipeline.run("please try again")

    assert node.calls == 2
