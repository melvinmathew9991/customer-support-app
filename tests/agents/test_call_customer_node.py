from langchain.output_parsers import PydanticOutputParser

from customer_support_app.agents import support
from customer_support_app.agents.support import CallCustomerNode
from customer_support_app.domain.chat import Role
from customer_support_app.domain.validation import PhoneCallRequest, PhoneCallTicket


def _node_with_input(phone_number: str) -> CallCustomerNode:
    # Bypass __init__: it builds a tool-calling agent, which needs a real chat model.
    node = CallCustomerNode.__new__(CallCustomerNode)
    node.set_node_input(PhoneCallRequest(phone_number=phone_number))
    return node


def test_greeting_completes_without_audio_extra(monkeypatch):
    monkeypatch.setattr(support, "transcription_available", lambda: False)
    node = _node_with_input("555-0100")

    message = node.greeting_message()

    assert message.role == Role.ASSISTANT
    assert "555-0100" in message.message
    assert "ticket" not in message.message.lower()


def test_transcription_available_reflects_installed_modules(monkeypatch):
    from customer_support_app.tools import audio_transcribe

    monkeypatch.setattr(audio_transcribe.importlib.util, "find_spec", lambda name: None)
    assert audio_transcribe.transcription_available() is False

    monkeypatch.setattr(audio_transcribe.importlib.util, "find_spec", lambda name: object())
    assert audio_transcribe.transcription_available() is True


def _node_with_call_tool_output(monkeypatch, completion: str) -> CallCustomerNode:
    monkeypatch.setattr(support, "transcription_available", lambda: True)
    node = _node_with_input("555-0100")
    node._output_parser = PydanticOutputParser(pydantic_object=PhoneCallTicket)
    node._predict = lambda messages: completion
    return node


def test_greeting_falls_back_when_the_call_tool_returns_the_schema_not_a_ticket(monkeypatch):
    # What llama3.2:3b returned in #43: the ticket's JSON schema instead of a ticket.
    schema = PhoneCallTicket.model_json_schema()
    node = _node_with_call_tool_output(monkeypatch, str(schema).replace("'", '"'))

    message = node.greeting_message()

    assert message.role == Role.ASSISTANT
    assert "555-0100" in message.message
    assert "ticket summary" not in message.message.lower()


def test_greeting_reads_a_valid_ticket(monkeypatch):
    ticket = PhoneCallTicket(
        agent_name="Ruby", customer_name="Michael", call_summary="A POS issue."
    )
    node = _node_with_call_tool_output(monkeypatch, ticket.model_dump_json())

    message = node.greeting_message()

    assert "Ruby" in message.message
    assert "A POS issue." in message.message
