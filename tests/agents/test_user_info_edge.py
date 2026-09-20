import pytest
from langchain_core.exceptions import OutputParserException

from customer_support_app.agents.support import UserInfoChainBasedEdge
from customer_support_app.domain.chat import MessageHistory
from customer_support_app.domain.validation import UserProfile

MICHAEL = {
    "name": "Michael Jackson",
    "email": "michaeljackson@gmail.com",
    "user_id": "1",
    "phone": "0452 333 666",
    "language": "English",
}


class _Action:
    def __init__(self, tool, tool_input):
        self.tool = tool
        self.tool_input = tool_input


class _Extractor:
    """Stands in for the structured-output LLM; always returns the subscription it is given."""

    def __init__(self, subscription):
        self.subscription = subscription

    def invoke(self, prompt):
        return UserProfile(
            name="Michael Jackson",
            email="michaeljackson@gmail.com",
            subscription=self.subscription,
            user_id=1,
            phone="0452 333 666",
            language="English",
        )


def _edge(steps, extracted_subscription="free"):
    """An identity edge whose tool calls are scripted, with no LLM behind it."""
    edge = object.__new__(UserInfoChainBasedEdge)
    findings = "summary\n\nRaw tool results:\n" + "\n".join(
        f"- {action.tool} result: {observation}" for action, observation in steps
    )
    edge._gather_findings = lambda model_input: findings
    edge._last_intermediate_steps = steps
    edge._structured_llm = _Extractor(extracted_subscription)
    return edge


def _history() -> MessageHistory:
    history = MessageHistory(messages=[])
    history.add_assistant_message("please give your email")
    history.add_user_message("michaeljackson@gmail.com")
    return history


def _info_step(record=MICHAEL):
    return (_Action("user_info_db_search", "michaeljackson@gmail.com"), [record])


def _subscription_step(user_id="1", subscription="premium"):
    return (
        _Action("user_subscription_db_search", user_id),
        [{"user_id": user_id, "subscription": subscription}],
    )


def test_subscription_comes_from_the_db_record_not_the_extractor():
    edge = _edge([_info_step(), _subscription_step()], extracted_subscription="free")

    profile = edge._parse(_history())

    assert profile.subscription == "premium"
    assert profile.name == "Michael Jackson"


def test_a_free_text_subscription_from_the_extractor_is_replaced():
    edge = _edge(
        [_info_step(), _subscription_step()],
        extracted_subscription="user_subscription_db_search result",
    )

    assert edge._parse(_history()).subscription == "premium"


def test_skipped_subscription_lookup_fails_instead_of_letting_the_extractor_guess():
    edge = _edge([_info_step()], extracted_subscription="free")

    with pytest.raises(OutputParserException, match="never ran"):
        edge._parse(_history())


def test_empty_subscription_result_still_fails():
    steps = [_info_step(), (_Action("user_subscription_db_search", "1"), [])]

    with pytest.raises(OutputParserException, match="no subscription record"):
        _edge(steps)._parse(_history())


def test_subscription_record_of_a_different_user_is_rejected():
    steps = [_info_step(), _subscription_step(user_id="2", subscription="free")]

    with pytest.raises(OutputParserException, match="doesn't belong"):
        _edge(steps)._parse(_history())
