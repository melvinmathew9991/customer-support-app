from customer_support_app.agents import support
from customer_support_app.agents.support import CallCustomerNode
from customer_support_app.domain.chat import Role
from customer_support_app.domain.validation import PhoneCallRequest


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
