import pytest
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from customer_support_app.domain.chat import MessageHistory
from customer_support_app.graph.chain_based_node import (
    NOT_COVERED_REPLY,
    RetrievalNode,
    contradicted_restriction,
    drop_contradicted_yes,
    invents_steps,
    names_unsupported_place,
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
        # Plain-prose steps (rag-paid-012, rag-oos-012 on the Brightstall KB, #17).
        'Add it by going to the Brightstall POS app and selecting the "Settings" option.',
        "Follow the password reset instructions in your store admin.",
        "Open the POS app and choose Locations.",
        "Download and install the Brightstall POS app, then follow the guide.",
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


PAYMENTS_CONTEXT = (
    "With Brightstall Payments, you can check your pay period to see when your payouts for "
    "credit card orders will arrive.\n"
    "If you change banks, or your bank account details change, you can update them in your "
    "Brightstall Payments settings.\n"
    "The quickest way to report alleged copyright infringement is Brightstall's online form."
)


@pytest.mark.parametrize(
    "question, answer",
    [
        (
            "My bank account details changed. How do I update where I get paid?",
            "You can update your bank account details in your Brightstall Payments settings.",
        ),
        (
            "How do I submit a copyright infringement notice to Brightstall?",
            "You can submit it through their online form.",
        ),
        ("How do I check when I'll receive my payouts?", "Check your pay period."),
    ],
)
def test_a_place_the_context_gives_for_the_same_task_is_allowed(question, answer):
    assert names_unsupported_place(answer, PAYMENTS_CONTEXT, question) is False


@pytest.mark.parametrize(
    "question, answer",
    [
        # rag-free-011: the place belongs to the bank-details sentence, not to payouts.
        (
            "How do I check when I'll receive my payouts?",
            "You can check your pay period in your Brightstall Payments settings.",
        ),
        # rag-oos-012: a place that is nowhere in the context.
        (
            "How do I reset my admin password?",
            "You can reset it in your store admin.",
        ),
    ],
)
def test_a_place_the_context_never_gives_for_the_task_is_flagged(question, answer):
    assert names_unsupported_place(answer, PAYMENTS_CONTEXT, question) is True


def test_a_feature_the_context_never_names_is_flagged():
    # rag-oos-014: an invented product feature.
    assert names_unsupported_place(
        "You can print shipping labels by using the Brightstall shipping labels feature.",
        PAYMENTS_CONTEXT,
        "How do I print shipping labels for my orders?",
    ) is True


def test_a_place_named_for_a_task_mentioned_only_by_product_name_is_flagged():
    # rag-oos-011: "POS" names the product, not the task, so it cannot tie the place to it.
    context = "Brightstall POS syncs with your Brightstall admin to track orders."

    assert names_unsupported_place(
        "To connect a card reader, set up payments in your Brightstall admin.",
        context,
        "How do I connect a card reader to Brightstall POS?",
    ) is True


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


def test_predict_replaces_an_answer_that_names_an_unsupported_place():
    assert _ask("You can update them in your store admin.") == NOT_COVERED_REPLY


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


FREE_POS_CONTEXT = (
    "Selling in person: a free subscription does not include selling in person. On a free "
    "subscription you can sell online only.\n"
    "Because a free subscription has no in-person selling, you do not need any Brightstall POS "
    "hardware on this plan."
)


def test_an_answer_that_turns_a_restriction_around_is_replaced_by_the_restriction():
    # rag-adv-013.
    answer = (
        "You need to buy Brightstall POS hardware for your pop-up shop, as selling in person "
        "with Brightstall POS requires a paid subscription."
    )

    replacement = contradicted_restriction(answer, FREE_POS_CONTEXT)

    assert replacement is not None
    assert "you do not need any Brightstall POS hardware" in replacement


@pytest.mark.parametrize(
    "answer",
    [
        # Correct answers, including ones whose negation comes after the verb (rag-adv-004).
        "You do not need any Brightstall POS hardware, as selling in person is not included.",
        "No, a free subscription does not include selling in person.",
        "On a free subscription you can sell online only.",
    ],
)
def test_an_answer_that_keeps_the_restriction_is_left_alone(answer):
    assert contradicted_restriction(answer, FREE_POS_CONTEXT) is None


def test_a_leading_yes_that_the_answer_goes_on_to_deny_is_dropped():
    # rag-free-017.
    answer = (
        "Yes, an app that fulfills orders is treated as a location, but it does not count "
        "toward the location limit."
    )

    assert drop_contradicted_yes(
        answer, "Does an app that fulfills my orders count toward my location limit?"
    ) == (
        "An app that fulfills orders is treated as a location, but it does not count toward "
        "the location limit."
    )


def test_a_leading_yes_that_the_answer_supports_is_kept():
    answer = "Yes, you can accept manual payments such as money orders."

    assert drop_contradicted_yes(answer, "Can I accept money orders?") == answer


def test_predict_answers_with_the_restriction_when_the_answer_contradicts_it():
    answer = _Node("You need to buy POS hardware for your shop.", FREE_POS_CONTEXT)
    history = MessageHistory(messages=[])
    history.add_user_message("What POS hardware should I buy?")

    assert "you do not need any Brightstall POS hardware" in answer._predict(history)
