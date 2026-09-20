import sqlite3

import httpx
import pytest

from customer_support_app.domain.chat import Role
from customer_support_app.domain.graph import EdgeOutput, MessageOutput
from customer_support_app.domain.validation import PhoneCallRequest, UserProfile
from customer_support_app.pipeline import TIMEOUT_REPLY, CustomerSupportPipeline
from customer_support_app.session_store import SessionRecord, SessionStore

MICHAEL = UserProfile(
    name="Michael Jackson",
    email="michaeljackson@gmail.com",
    subscription="premium",
    user_id=1,
    phone="0452 333 666",
    language="English",
)


class _Edge:
    def __init__(self):
        self._num_fails = 0


class _FakeNode:
    """Stands in for a graph node; the class names match the real nodes, which the store keys on."""

    final = False

    def __init__(self, pipeline):
        self._pipeline = pipeline
        self._node_input = None

    def set_node_input(self, value):
        self._node_input = value

    def is_node_final(self):
        return self.final

    def greeting_message(self):
        return MessageOutput("hello", Role.ASSISTANT)

    def _last_user_message(self, history):
        return history.role_based_history(Role.USER)[-1]["content"]


class GreetingNode(_FakeNode):
    def execute(self, history):
        text = self._last_user_message(history)
        if "@" not in text:
            self._pipeline._user_info_chain._num_fails += 1
            return MessageOutput("please give your email", Role.ASSISTANT)
        self._pipeline._help_node.set_node_input(MICHAEL)
        return EdgeOutput(
            should_continue=True,
            result=MICHAEL,
            message_output=[MessageOutput("User Info retrieved", Role.SYSTEM)],
            num_fails=0,
            next_node=self._pipeline._help_node,
        )


class AuthenticatedUserNode(_FakeNode):
    def greeting_message(self):
        return MessageOutput(f"Hi {self._node_input.name}", Role.ASSISTANT)

    def execute(self, history):
        text = self._last_user_message(history)
        if "call" in text:
            call_node = self._pipeline._call_customer_node
            call_node.set_node_input(PhoneCallRequest(phone_number="0452 333 666"))
            return EdgeOutput(
                should_continue=True,
                result=None,
                message_output=None,
                num_fails=0,
                next_node=call_node,
            )
        profile = self._node_input
        return MessageOutput(f"{profile.name}, on {profile.subscription}", Role.ASSISTANT)


class CallCustomerNode(_FakeNode):
    final = True

    def greeting_message(self):
        return MessageOutput("we will call", Role.ASSISTANT)


class _TimingOutNode(GreetingNode):
    def execute(self, history):
        raise httpx.ReadTimeout("no answer")


@pytest.fixture(autouse=True)
def fake_graph(monkeypatch):
    """Replaces graph construction, which would need a Chroma index and a running Ollama."""
    calls = {"built": 0}

    def _get_pipeline(self):
        calls["built"] += 1
        self._call_customer_node = CallCustomerNode(self)
        self._call_customer_edge = _Edge()
        self._help_node = AuthenticatedUserNode(self)
        self._user_info_chain = _Edge()
        self._start_node = GreetingNode(self)
        return self._start_node

    monkeypatch.setattr(CustomerSupportPipeline, "_get_pipeline", _get_pipeline)
    return calls


@pytest.fixture
def store(tmp_path):
    return SessionStore(tmp_path / "sessions.sqlite")


def _identified(store, session_id="s1"):
    pipeline = CustomerSupportPipeline(store=store, session_id=session_id)
    pipeline.run("")
    pipeline.run("michaeljackson@gmail.com")
    return pipeline


def test_without_a_store_nothing_is_saved_and_there_is_no_session(tmp_path):
    pipeline = CustomerSupportPipeline()

    pipeline.run("")
    pipeline.run("michaeljackson@gmail.com")

    assert pipeline.session_id is None
    assert pipeline.resumed is False
    assert list(tmp_path.iterdir()) == []


def test_a_store_without_a_session_id_gets_a_new_one(store):
    pipeline = CustomerSupportPipeline(store=store)

    assert pipeline.session_id
    assert pipeline.resumed is False


def test_the_greeting_turn_is_saved(store):
    pipeline = CustomerSupportPipeline(store=store, session_id="s1")

    pipeline.run("")

    saved = store.load("s1")
    assert saved.node == "GreetingNode"
    assert saved.node_input is None
    assert saved.messages == [{"content": "hello", "role": "assistant"}]
    assert saved.is_over is False


def test_a_conversation_resumes_at_the_same_node_with_everything_it_had(store, fake_graph):
    first = _identified(store)
    first.run("What are your payment options?")

    second = CustomerSupportPipeline(store=store, session_id="s1")

    assert second.resumed is True
    assert type(second._current_node).__name__ == "AuthenticatedUserNode"
    assert second._current_node._node_input == MICHAEL
    assert second._message_history.messages == first._message_history.messages
    assert second._conversation_id == first._conversation_id
    # The restored node still works: it answers from the restored profile, not a fresh one.
    replies, is_over = second.run("and free plans?")
    assert [r.message for r in replies] == ["Michael Jackson, on premium"]
    assert is_over is False


def test_resuming_does_not_run_the_greeting_again(store):
    _identified(store)
    before = store.load("s1").messages

    resumed = CustomerSupportPipeline(store=store, session_id="s1")

    assert resumed._message_history.messages == before
    assert resumed.transcript()[0] == {"content": "hello", "role": "assistant"}


def test_the_transcript_leaves_out_internal_system_lines(store):
    resumed = CustomerSupportPipeline(store=_store_after_identification(store), session_id="s1")

    roles = [m["role"] for m in resumed.transcript()]

    assert roles == ["assistant", "user", "assistant"]
    assert "User Info retrieved" not in [m["content"] for m in resumed.transcript()]


def _store_after_identification(store):
    _identified(store)
    return store


def test_the_retry_counter_of_a_half_finished_identification_is_restored(store):
    pipeline = CustomerSupportPipeline(store=store, session_id="s1")
    pipeline.run("")
    pipeline.run("hey")
    pipeline.run("what's up")

    resumed = CustomerSupportPipeline(store=store, session_id="s1")

    assert type(resumed._current_node).__name__ == "GreetingNode"
    assert resumed._user_info_chain._num_fails == 2
    assert resumed._call_customer_edge._num_fails == 0


def test_an_ended_conversation_resumes_as_ended(store):
    pipeline = _identified(store)
    replies, is_over = pipeline.run("please call me")
    assert is_over is True

    resumed = CustomerSupportPipeline(store=store, session_id="s1")

    assert resumed.resumed is True
    assert resumed.ended is True
    assert type(resumed._current_node).__name__ == "CallCustomerNode"
    assert store.latest_unfinished() is None


def test_the_graph_is_built_once_when_a_session_resumes_and_then_continues(store, fake_graph):
    _identified(store)
    fake_graph["built"] = 0

    CustomerSupportPipeline(store=store, session_id="s1")

    assert fake_graph["built"] == 1


def test_an_unknown_session_id_starts_a_new_conversation_under_that_id(store):
    pipeline = CustomerSupportPipeline(store=store, session_id="brand-new")

    assert pipeline.session_id == "brand-new"
    assert pipeline.resumed is False
    pipeline.run("")
    assert store.load("brand-new").node == "GreetingNode"


_FAILED_ID = {"message": "could not verify", "role": "system"}


def _save_raw(store, **overrides):
    fields = dict(
        session_id="bad",
        conversation_id="c",
        node="AuthenticatedUserNode",
        node_input={"type": "UserProfile", "data": MICHAEL.model_dump()},
        edge_fails={},
        messages=[{"content": "hello", "role": "assistant"}],
        is_over=False,
    )
    fields.update(overrides)
    store.save(SessionRecord(**fields))


@pytest.mark.parametrize(
    ("overrides", "why"),
    [
        (
            {"node_input": {"type": "MessageOutput", "data": _FAILED_ID}},
            "usable input",
        ),
        ({"node": "GhostNode"}, "unknown node"),
        ({"node_input": None}, "usable input"),
        ({"node": "GreetingNode"}, "usable input"),
        ({"node_input": {"type": "UserProfile", "data": {"name": "only a name"}}}, ""),
        ({"node_input": {"type": "Unheard", "data": {}}}, ""),
        ({"edge_fails": {"UserInfoChainBasedEdge": -1}}, "retry counters"),
        ({"edge_fails": {"CallCustomerEdge": "two"}}, "retry counters"),
    ],
)
def test_a_saved_session_that_cannot_be_resumed_starts_a_new_conversation(
    store, caplog, overrides, why
):
    _save_raw(store, **overrides)

    with caplog.at_level("WARNING", logger="customer_support_app.pipeline"):
        pipeline = CustomerSupportPipeline(store=store, session_id="bad")

    assert pipeline.resumed is False
    assert pipeline._current_node is None
    assert pipeline._message_history.messages == []
    messages = [r.getMessage() for r in caplog.records]
    assert any("cannot be resumed" in m and why in m for m in messages)

    replies, _ = pipeline.run("")
    assert [r.message for r in replies] == ["hello"]
    assert store.load("bad").node == "GreetingNode"


def test_a_failed_save_does_not_break_the_turn(store, monkeypatch, caplog):
    pipeline = CustomerSupportPipeline(store=store, session_id="s1")

    def _broken(record):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(store, "save", _broken)

    with caplog.at_level("WARNING", logger="customer_support_app.pipeline"):
        replies, _ = pipeline.run("")

    assert [r.message for r in replies] == ["hello"]
    assert any("Could not save session" in r.getMessage() for r in caplog.records)


def test_a_timed_out_turn_is_saved_with_its_reply(store):
    pipeline = _identified(store)
    pipeline._current_node = _TimingOutNode(pipeline)

    replies, _ = pipeline.run("tell me something")

    assert [r.message for r in replies] == [TIMEOUT_REPLY]
    saved = store.load("s1")
    assert saved.messages[-2:] == [
        {"content": "tell me something", "role": "user"},
        {"content": TIMEOUT_REPLY, "role": "assistant"},
    ]


def test_a_crash_mid_turn_saves_nothing_from_that_turn(store):
    pipeline = _identified(store)
    saved_before = store.load("s1")

    class _Exploding(GreetingNode):
        def execute(self, history):
            raise RuntimeError("model server died")

    pipeline._current_node = _Exploding(pipeline)
    with pytest.raises(RuntimeError):
        pipeline.run("this message is lost")

    assert store.load("s1") == saved_before


def test_two_sessions_do_not_leak_into_each_other(store):
    _identified(store, "a")
    other = CustomerSupportPipeline(store=store, session_id="b")
    other.run("")

    assert type(CustomerSupportPipeline(store=store, session_id="a")._current_node).__name__ == (
        "AuthenticatedUserNode"
    )
    assert type(CustomerSupportPipeline(store=store, session_id="b")._current_node).__name__ == (
        "GreetingNode"
    )
