import pytest

from customer_support_app.agents.support import CallCustomerEdge
from customer_support_app.domain.chat import MessageHistory
from customer_support_app.domain.validation import PhoneCallRequest, Validation


class _CountingLLM:
    """Stands in for a chat model whose intent check always says yes; counts calls."""

    def __init__(self):
        self.calls = 0

    def with_structured_output(self, schema):
        llm = self

        class _Bound:
            def invoke(self, prompt):
                llm.calls += 1
                return Validation(is_valid=True)

        return _Bound()


def _history(last_user_message: str) -> MessageHistory:
    history = MessageHistory(messages=[])
    history.add_assistant_message("welcome")
    history.add_user_message("me@example.com")
    history.add_system_message("User Info retrieved: phone='0452 333 666'")
    history.add_user_message(last_user_message)
    return history


@pytest.mark.parametrize(
    "message",
    [
        "What are your customer support hours and how do I reach a human by phone for billing?",
        "What phone-based payment methods do you support?",
        "please call me",
        "my order is 1234",
    ],
)
def test_no_phone_number_never_reaches_intent_check(message):
    llm = _CountingLLM()
    edge = CallCustomerEdge(llm_model=llm)

    assert edge.check(_history(message)) is False
    assert llm.calls == 0


@pytest.mark.parametrize(
    "message",
    [
        "please call me at 0452 111 222",
        "call me on 0452-111-222",
        "ring me back, my number is (0452) 111 222",
        "call +61 452 111 222",
    ],
)
def test_message_with_phone_number_defers_to_intent_check(message):
    llm = _CountingLLM()
    edge = CallCustomerEdge(llm_model=llm)

    assert edge.check(_history(message)) is True
    assert llm.calls == 1


class _ExtractingLLM:
    """Intent check says yes; extraction returns a fixed phone number."""

    def __init__(self, phone_number):
        self.phone_number = phone_number

    def with_structured_output(self, schema):
        llm = self

        class _Bound:
            def invoke(self, prompt):
                if schema is PhoneCallRequest:
                    return PhoneCallRequest(phone_number=llm.phone_number)
                return Validation(is_valid=True)

        return _Bound()


@pytest.mark.parametrize(
    "message, extracted",
    [
        ("call me on 0452 222 111", "0452 222 111"),
        ("call me on 0452 222 111", "0452222111"),
        ("call me on 0452-222-111 please", "0452 222 111"),
        ("call me back, +61 452 222 111", "+61 452 222 111"),
    ],
)
def test_extracted_number_found_in_the_users_message_starts_the_callback(message, extracted):
    edge = CallCustomerEdge(llm_model=_ExtractingLLM(extracted))

    output = edge.execute(_history(message))

    assert output.should_continue is True
    assert output.result.phone_number == extracted


@pytest.mark.parametrize(
    "message, extracted, typed",
    [
        ("call me on 0452 222 111", "0452 333 666", "0452 222 111"),
        ("call me on 0452 222 111", "+61 452 222 111", "0452 222 111"),
        ("call me on 0452 222 111", "", "0452 222 111"),
        ("call me on 0452 222 111", "no number", "0452 222 111"),
        (
            "Could someone ring me back? My number is 0452 555 111",
            "0452255111",
            "0452 555 111",
        ),
        ("my work line is (03) 9555 0177, call me there", "0395550188", "(03) 9555 0177"),
        ("call me back, +61 452 222 111", "0452 222 111", "+61 452 222 111"),
    ],
)
def test_extracted_number_not_in_the_users_message_falls_back_to_the_typed_number(
    message, extracted, typed
):
    edge = CallCustomerEdge(llm_model=_ExtractingLLM(extracted))

    output = edge.execute(_history(message))

    assert output.should_continue is True
    assert output.result.phone_number == typed


@pytest.mark.parametrize(
    "message",
    [
        "my old number was 0452 909 120, call me on 0452 810 274",
        "call 0452 111 222 or 0452 333 444",
    ],
)
def test_wrong_extraction_with_several_numbers_never_starts_the_callback(message):
    edge = CallCustomerEdge(llm_model=_ExtractingLLM("0452 333 666"))

    output = edge.execute(_history(message))

    assert output.should_continue is False
    assert not isinstance(output.result, PhoneCallRequest)


def test_profile_phone_in_system_message_does_not_count_as_user_supplied():
    llm = _CountingLLM()
    edge = CallCustomerEdge(llm_model=llm)

    assert edge.check(_history("call me back please")) is False
    assert llm.calls == 0
