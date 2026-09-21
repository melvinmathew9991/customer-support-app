import pytest

from customer_support_app.agents.support import CallCustomerEdge
from customer_support_app.domain.chat import MessageHistory
from customer_support_app.domain.validation import PhoneCallRequest, Validation


class _CountingLLM:
    """Stands in for a chat model whose intent check always gives one answer; counts calls."""

    def __init__(self, answer=True):
        self.calls = 0
        self.answer = answer

    def with_structured_output(self, schema):
        llm = self

        class _Bound:
            def invoke(self, prompt):
                llm.calls += 1
                return Validation(is_valid=llm.answer)

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
        "reach me on 0452-111-222 when you can",
        "my number is (0452) 111 222, I'd like a chat by phone",
        "+61 452 111 222 is the best number for me",
        "call +61 452 111 222",
    ],
)
def test_message_without_a_plain_request_defers_to_intent_check(message):
    llm = _CountingLLM()
    edge = CallCustomerEdge(llm_model=llm)

    assert edge.check(_history(message)) is True
    assert llm.calls == 1


def test_intent_check_saying_no_is_respected_for_a_message_without_a_plain_request():
    llm = _CountingLLM(answer=False)
    edge = CallCustomerEdge(llm_model=llm)

    assert edge.check(_history("is 0452 111 222 the number for your store?")) is False
    assert llm.calls == 1


@pytest.mark.parametrize(
    "message",
    [
        "please call me at 0452 111 222",
        "call me on 0452-111-222",
        "ring me back, my number is (0452) 111 222",
        "Can you give me a call on 0452 111 222?",
        "someone should phone 0452 111 222",
        "call this number 0452 111 222",
        "0452 111 222 - callback please",
    ],
)
def test_plain_request_is_accepted_without_asking_the_model(message):
    llm = _CountingLLM(answer=False)
    edge = CallCustomerEdge(llm_model=llm)

    assert edge.check(_history(message)) is True
    assert llm.calls == 0


@pytest.mark.parametrize(
    "message",
    [
        "do not call me, my number is 0452 111 222 for texts",
        "I'd rather have no calls. 0452 111 222 is my mobile",
        "never call me on 0452 111 222",
        "please don't call me, ring 0452 111 222 only in an emergency",
        "No need to call me back, my number is 0452 333 666 if you want to email",
        "There is no need for you to phone me. 0452 111 222 is my mobile",
    ],
)
def test_asking_not_to_be_called_is_rejected_without_asking_the_model(message):
    llm = _CountingLLM(answer=True)
    edge = CallCustomerEdge(llm_model=llm)

    assert edge.check(_history(message)) is False
    assert llm.calls == 0


@pytest.mark.parametrize(
    "message",
    [
        "Never call me before 9am, but do call me on 0452 333 666 after.",
        "Please don't call me at work, but call me on 0452 111 222 after 5pm.",
        "Call me on 0452 222 333 please, but don't call the landline.",
        "No need to call the office, just call me on 0452 121 343.",
        "Do not phone me before noon, but give me a call on 0452 909 808 after that.",
    ],
)
def test_a_request_is_accepted_even_when_the_same_message_declines_something_else(message):
    llm = _CountingLLM(answer=False)
    edge = CallCustomerEdge(llm_model=llm)

    assert edge.check(_history(message)) is True
    assert llm.calls == 0


@pytest.mark.parametrize(
    "message",
    [
        "Never call me on 0452 333 666, email me instead.",
        "Don't call me, but do email me; my number is 0452 555 000 in case you need it.",
        "No calls please. If you must, the number is 0452 616 262 but don't call before 9.",
        "Please don't call me back on 0452 111 222",
    ],
)
def test_a_decline_with_nothing_else_asked_is_still_rejected_without_asking_the_model(message):
    llm = _CountingLLM(answer=True)
    edge = CallCustomerEdge(llm_model=llm)

    assert edge.check(_history(message)) is False
    assert llm.calls == 0


@pytest.mark.parametrize(
    "message",
    [
        "Your site says call us on 1300 655 021, is that right?",
        "I called 0452 314 559 yesterday and nobody answered",
    ],
)
def test_quoting_a_number_to_call_or_a_past_call_is_left_to_the_model(message):
    llm = _CountingLLM(answer=False)
    edge = CallCustomerEdge(llm_model=llm)

    assert edge.check(_history(message)) is False
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
