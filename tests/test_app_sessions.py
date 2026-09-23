"""Drives the real app.py headlessly with a stand-in pipeline (no LLM, Chroma or network)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import customer_support_app.config as config
import customer_support_app.logging_config as logging_config
import customer_support_app.pipeline as pipeline_module
from customer_support_app.agents.support import GreetingNode as RealGreetingNode
from customer_support_app.domain.chat import Role
from customer_support_app.domain.graph import MessageOutput
from customer_support_app.domain.validation import UserProfile
from customer_support_app.session_store import SessionRecord, SessionStore, SessionStoreError

APP = Path(__file__).resolve().parents[1] / "src" / "customer_support_app" / "app.py"


class GreetingNode:
    pass


class AuthenticatedUserNode:
    pass


class CallCustomerNode:
    pass


_NODES = {c.__name__: c for c in (GreetingNode, AuthenticatedUserNode, CallCustomerNode)}


class _FakePipeline:
    """Saves and loads through the real store, like the real pipeline does."""

    created = []

    def __init__(self, store, session_id):
        self._store = store
        self.session_id = session_id
        record = store.load(session_id)
        self.resumed = record is not None
        self._messages = list(record.messages) if record else []
        self._node = record.node if record else "GreetingNode"
        self._over = bool(record and record.is_over)
        self._current_node = _NODES[self._node]()
        self.received = []
        self.current_user_profile = None
        _FakePipeline.created.append(self)

    @property
    def ended(self):
        return self._over

    def transcript(self):
        return [m for m in self._messages if m["role"] in ("user", "assistant")]

    def run(self, text):
        self.received.append(text)
        if text == "":
            reply = "hello, who are you?"
        elif text == "call me":
            reply, self._node, self._over = "we will call you", "CallCustomerNode", True
        elif text == "gibberish":
            reply = RealGreetingNode.RETRY_PROMPT[0]
        else:
            reply, self._node = f"echo: {text}", "AuthenticatedUserNode"
        if text:
            self._messages.append({"content": text, "role": "user"})
        self._messages.append({"content": reply, "role": "assistant", "node": self._node})
        self._current_node = _NODES[self._node]()
        self._store.save(
            SessionRecord(
                self.session_id, "conv", self._node, None, {}, self._messages, self._over
            )
        )
        return [MessageOutput(reply, Role.ASSISTANT)], self._over


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "sessions.sqlite"
    settings = config.Settings(session_db_path=path)
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    monkeypatch.setattr(pipeline_module, "CustomerSupportPipeline", _FakePipeline)
    # The real setup would attach a file handler for the project's own logs/turns.jsonl.
    monkeypatch.setattr(logging_config, "setup_logging", lambda: None)
    _FakePipeline.created.clear()
    import streamlit as st

    st.cache_resource.clear()
    return path


def _open(session=None):
    at = AppTest.from_file(str(APP), default_timeout=30)
    if session is not None:
        at.query_params["session"] = session
    return at.run()


def _texts(at):
    return [md.value for cm in at.chat_message for md in cm.markdown]


def _success_texts(at):
    return [s.value for cm in at.chat_message for s in cm.success]


def test_a_first_visit_creates_a_session_and_puts_its_id_in_the_url(db):
    at = _open()

    assert not at.exception
    session = at.query_params["session"][0]
    assert len(session) == 32
    assert _FakePipeline.created[0].session_id == session
    assert _texts(at) == ["hello, who are you?"]
    assert SessionStore(db).load(session) is not None


def test_a_page_reload_with_the_same_url_resumes_and_does_not_greet_again(db):
    first = _open()
    session = first.query_params["session"][0]
    first.chat_input[0].set_value("michaeljackson@gmail.com").run()

    reloaded = _open(session)

    assert not reloaded.exception
    assert _FakePipeline.created[-1].resumed is True
    assert _FakePipeline.created[-1].received == []  # no run("") for the greeting
    assert _texts(reloaded) == [
        "hello, who are you?",
        "michaeljackson@gmail.com",
        "echo: michaeljackson@gmail.com",
    ]
    assert reloaded.query_params["session"] == [session]


def test_a_resumed_conversation_carries_on_and_saves_the_new_turn(db):
    first = _open()
    session = first.query_params["session"][0]
    first.chat_input[0].set_value("hi").run()

    resumed = _open(session)
    resumed.chat_input[0].set_value("and another thing").run()

    assert _texts(resumed)[-2:] == ["and another thing", "echo: and another thing"]
    saved = SessionStore(db).load(session)
    assert [m["content"] for m in saved.messages][-2:] == [
        "and another thing",
        "echo: and another thing",
    ]


def test_two_urls_are_two_separate_conversations(db):
    a = _open("aaa")
    a.chat_input[0].set_value("from a").run()

    b = _open("bbb")

    assert _texts(b) == ["hello, who are you?"]
    assert "from a" not in _texts(b)


def test_an_ended_conversation_shows_its_transcript_and_no_longer_takes_input(db):
    first = _open()
    session = first.query_params["session"][0]
    first.chat_input[0].set_value("call me").run()
    assert [i.value for i in first.info] == ["This conversation has ended."]

    resumed = _open(session)

    assert _success_texts(resumed) == ["we will call you"]
    assert [i.value for i in resumed.info] == ["This conversation has ended."]
    assert resumed.chat_input[0].disabled is True
    assert [b.label for b in resumed.button] == ["Start a new conversation"]


def test_start_a_new_conversation_clears_the_session_and_begins_again(db):
    first = _open()
    old = first.query_params["session"][0]
    first.chat_input[0].set_value("call me").run()

    first.button[0].click().run()

    # The click clears the URL and the session and calls st.rerun(). AppTest does not refresh
    # its element tree for a rerun made inside a run, so check the state, then run once more
    # to see what the user would be shown.
    new = first.query_params["session"][0]
    assert new != old
    assert [m["content"] for m in first.session_state.messages] == ["hello, who are you?"]
    first.run()
    assert _texts(first) == ["hello, who are you?"]
    assert not first.info
    assert first.query_params["session"][0] == new


def test_a_database_from_a_newer_version_shows_an_error_and_stops(db, monkeypatch):
    def _refuse(path):
        raise SessionStoreError("uses session schema 99")

    monkeypatch.setattr("customer_support_app.session_store.SessionStore", _refuse)

    at = _open()

    assert [e.value for e in at.error] == [
        "Cannot use the saved-conversation database: uses session schema 99"
    ]
    assert not at.chat_input


def test_a_live_callback_message_renders_as_a_success_message(db):
    at = _open()
    at.chat_input[0].set_value("call me").run()

    # docs/Design.md §4: ticket-confirmation messages render as a success message, not
    # plain markdown.
    assert _success_texts(at) == ["we will call you"]
    assert "we will call you" not in _texts(at)


def test_a_retry_prompt_renders_as_a_warning_message(db):
    at = _open()
    at.chat_input[0].set_value("gibberish").run()

    assert [w.value for cm in at.chat_message for w in cm.warning] == [
        RealGreetingNode.RETRY_PROMPT[0]
    ]
    assert RealGreetingNode.RETRY_PROMPT[0] not in _texts(at)


def test_a_resumed_session_still_recognizes_a_retry_prompt_from_its_history(db):
    first = _open()
    session = first.query_params["session"][0]
    first.chat_input[0].set_value("gibberish").run()

    resumed = _open(session)

    assert [w.value for cm in resumed.chat_message for w in cm.warning] == [
        RealGreetingNode.RETRY_PROMPT[0]
    ]


def test_a_resumed_session_still_renders_its_ticket_confirmation_as_a_success_message(db):
    first = _open()
    session = first.query_params["session"][0]
    first.chat_input[0].set_value("call me").run()

    resumed = _open(session)

    assert _success_texts(resumed) == ["we will call you"]
    assert "we will call you" not in _texts(resumed)


def test_a_session_saved_before_replies_carried_their_node_replays_as_plain_text(db):
    messages = [
        {"content": "hello, who are you?", "role": "assistant"},
        {"content": "call me", "role": "user"},
        {"content": "we will call you", "role": "assistant"},
    ]
    SessionStore(db).save(
        SessionRecord("old", "conv", "CallCustomerNode", None, {}, messages, True)
    )

    resumed = _open("old")

    assert not resumed.exception
    assert _texts(resumed) == ["hello, who are you?", "call me", "we will call you"]
    assert _success_texts(resumed) == []


def test_no_subscription_badge_before_identification(db):
    at = _open()

    assert not at.caption


def test_a_subscription_badge_appears_once_identified(db):
    at = _open()
    _FakePipeline.created[-1].current_user_profile = UserProfile(
        name="John Doe",
        email="john@doe.com",
        subscription="free",
        user_id=2,
        phone="0452 333 667",
        language="English",
    )

    at.chat_input[0].set_value("hi").run()

    assert [c.value for c in at.caption] == ["John Doe · free plan"]
