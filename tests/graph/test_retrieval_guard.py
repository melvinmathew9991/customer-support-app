import pytest
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from customer_support_app.domain.chat import MessageHistory
from customer_support_app.graph.chain_based_node import (
    NOT_COVERED_REPLY,
    RetrievalNode,
    invents_steps,
)

CONTEXT = "You can update the bank account information in your Brightstall Payments settings."


@pytest.mark.parametrize(
    "answer",
    [
        # Real answers from the eval that invented steps (rag-free-006, rag-oos-007).
        'Go to Settings > Payments > Bank Account, and click "Edit".',
        'To cancel, go to your store admin, click on "Settings" and then "Account".',
        "Navigate to the Payments page.",
        "Tap the menu icon and choose Payments.",
        "Open Settings>Payments and save.",
        "Clicking the button saves it.",
    ],
)
def test_invented_navigation_is_detected(answer):
    assert invents_steps(answer, CONTEXT) is True


@pytest.mark.parametrize(
    "answer",
    [
        "You can update the information in your Brightstall Payments settings.",
        NOT_COVERED_REPLY,
        "Yes, you can accept manual payment methods like bank transfers.",
        "You have two days to respond before the content is removed.",
    ],
)
def test_grounded_answers_are_not_flagged(answer):
    assert invents_steps(answer, CONTEXT) is False


def test_navigation_wording_that_the_context_itself_uses_is_allowed():
    context = "Click Edit next to your bank account to change it."

    assert invents_steps("Click Edit to change it.", context) is False
    assert invents_steps("Click Edit, then tap Save.", context) is True  # 'tap' is not in context


class _Node(RetrievalNode):
    """A RetrievalNode with a canned retriever and a canned model (no Ollama)."""

    def __init__(self, answer, context):
        self._retriever = RunnableLambda(lambda _query: [Document(page_content=context)])
        super().__init__(
            llm_model=RunnableLambda(lambda _prompt: answer), pydantic_object=None, edges=[]
        )

    def _get_retriever(self):
        return self._retriever

    def greeting_message(self):
        return None

    def no_edges_found(self, user_input):
        return None


def _ask(answer, context=CONTEXT):
    history = MessageHistory(messages=[])
    history.add_user_message("How do I update my bank details?")
    return _Node(answer, context)._predict(history)


def test_predict_replaces_an_answer_that_invents_steps():
    assert _ask('Go to Settings > Payments and click "Edit".') == NOT_COVERED_REPLY


def test_predict_passes_a_grounded_answer_through_unchanged():
    answer = "You can update the information in your Brightstall Payments settings."

    assert _ask(answer) == answer


def test_predict_warns_when_the_retrieval_log_cannot_be_built(caplog):
    # The canned retriever has no vectorstore, so the scored lookup used for the turn
    # log fails; the answer must still come back, and the failure must not be silent.
    with caplog.at_level("WARNING", logger="customer_support_app.graph.chain_based_node"):
        answer = _ask("You can update it in your Brightstall Payments settings.")

    assert answer == "You can update it in your Brightstall Payments settings."
    assert any("retrieved documents" in record.getMessage() for record in caplog.records)
