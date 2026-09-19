from pydantic import BaseModel

from customer_support_app.domain.chat import MessageHistory
from customer_support_app.domain.validation import Validation
from customer_support_app.graph.text_based_edge import PydanticTextBasedEdge


class _RecordingLLM:
    """Stands in for a chat model: records the prompt sent to the yes/no check."""

    def __init__(self):
        self.prompts = []

    def with_structured_output(self, schema):
        llm = self

        class _Bound:
            def invoke(self, prompt):
                llm.prompts.append(prompt)
                return Validation(is_valid=True)

        return _Bound()


class _Anything(BaseModel):
    value: str = ""


class _TestEdge(PydanticTextBasedEdge):
    def _get_message_output(self, msg_input):
        return None


def _edge(llm):
    return _TestEdge(
        condition="is it a test?", parse_prompt="parse", parse_class=_Anything, llm_model=llm
    )


def test_check_excludes_system_messages_from_history():
    llm = _RecordingLLM()
    history = MessageHistory(messages=[])
    history.add_assistant_message("welcome")
    history.add_user_message("me@example.com")
    history.add_system_message("User Info retrieved: phone='0452 333 666'")
    history.add_assistant_message("Hi Sam")
    history.add_user_message("please call me")

    assert _edge(llm).check(history) is True

    prompt = llm.prompts[0]
    assert "User Info retrieved" not in prompt
    assert "0452 333 666" not in prompt
    assert "assistant: welcome" in prompt
    assert "user: me@example.com" in prompt
    assert "User's latest message: please call me" in prompt


def test_check_does_not_repeat_latest_message_in_history():
    llm = _RecordingLLM()
    history = MessageHistory(messages=[])
    history.add_assistant_message("welcome")
    history.add_user_message("latest question")

    _edge(llm).check(history)

    history_section = llm.prompts[0].split("Condition:")[0]
    assert "latest question" not in history_section
