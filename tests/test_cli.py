import pytest

from customer_support_app import cli
from customer_support_app.domain.chat import Role
from customer_support_app.domain.graph import MessageOutput
from customer_support_app.session_store import SessionStoreError


class _Pipeline:
    """Replays scripted replies; the conversation ends when the script says so."""

    def __init__(self, replies, session_id="sess-1", resumed=False, ended=False, transcript=()):
        self.replies = list(replies)
        self.received = []
        self.session_id = session_id
        self.resumed = resumed
        self.ended = ended
        self._transcript = list(transcript)

    def transcript(self):
        return self._transcript

    def run(self, user_input):
        self.received.append(user_input)
        message, is_over = self.replies.pop(0)
        return [MessageOutput(message, Role.ASSISTANT)], is_over


class _Store:
    def __init__(self, latest=None):
        self.latest = latest

    def latest_unfinished(self):
        return self.latest


@pytest.fixture
def cli_with(monkeypatch):
    def _install(replies=(), typed=(), store=None, **pipeline_options):
        pipeline = _Pipeline(replies, **pipeline_options)
        store = store or _Store()
        typed = iter(typed)
        built = {}

        def _input():
            try:
                return next(typed)
            except StopIteration:
                raise EOFError

        def _make_pipeline(store, session_id):
            built["session_id"] = session_id
            return pipeline

        monkeypatch.setattr(cli, "setup_logging", lambda: None)
        monkeypatch.setattr(cli, "SessionStore", lambda path: store)
        monkeypatch.setattr(cli, "CustomerSupportPipeline", _make_pipeline)
        monkeypatch.setattr("builtins.input", _input)
        pipeline.built = built
        return pipeline

    return _install


def test_end_of_input_ends_the_session_cleanly(cli_with, capsys):
    pipeline = cli_with([("welcome", False)], typed=[])

    assert cli.main([]) is None

    assert capsys.readouterr().out.splitlines()[-2:] == ["welcome", cli.GOODBYE]
    assert pipeline.received == [""]


@pytest.mark.parametrize("command", ["quit", "exit", "  Quit  ", "EXIT"])
def test_quit_and_exit_end_the_session_without_reaching_the_pipeline(cli_with, capsys, command):
    pipeline = cli_with([("welcome", False)], typed=[command])

    cli.main([])

    assert capsys.readouterr().out.splitlines()[-1] == cli.GOODBYE
    assert pipeline.received == [""]


def test_a_normal_conversation_runs_to_its_own_end_without_a_goodbye(cli_with, capsys):
    pipeline = cli_with(
        [("welcome", False), ("hello", False), ("bye", True)], typed=["hi", "thanks"]
    )

    cli.main([])

    out = capsys.readouterr().out.splitlines()
    assert out[-3:] == ["welcome", "hello", "bye"]
    assert cli.GOODBYE not in out
    assert pipeline.received == ["", "hi", "thanks"]


def test_a_new_conversation_prints_its_id_and_how_to_resume_it(cli_with, capsys):
    pipeline = cli_with([("welcome", True)], session_id="abc123")

    cli.main([])

    out = capsys.readouterr().out
    assert "customer-support-chat --session abc123" in out
    assert pipeline.built["session_id"] is None


def test_session_resumes_a_saved_conversation_without_greeting_again(cli_with, capsys):
    pipeline = cli_with(
        [("answer", False)],
        typed=["next question"],
        resumed=True,
        transcript=[
            {"role": "assistant", "content": "welcome"},
            {"role": "user", "content": "me@example.com"},
            {"role": "assistant", "content": "Hi Michael"},
        ],
    )

    cli.main(["--session", "sess-1"])

    out = capsys.readouterr().out.splitlines()
    assert pipeline.built["session_id"] == "sess-1"
    assert "Resuming conversation sess-1." in out
    assert out[-5:-1] == ["welcome", "You: me@example.com", "Hi Michael", "answer"]
    assert pipeline.received == ["next question"]  # no run("") for the greeting


def test_resuming_an_ended_conversation_shows_it_and_says_so(cli_with, capsys):
    pipeline = cli_with(
        typed=["should never be read"],
        resumed=True,
        ended=True,
        transcript=[{"role": "assistant", "content": "we will call you"}],
    )

    cli.main(["--session", "sess-1"])

    out = capsys.readouterr().out
    assert "we will call you" in out
    assert "This conversation has ended" in out
    assert pipeline.received == []


def test_resume_picks_the_latest_unfinished_conversation(cli_with):
    pipeline = cli_with(store=_Store(latest="latest-one"), resumed=True, typed=[])

    cli.main(["--resume"])

    assert pipeline.built["session_id"] == "latest-one"


def test_resume_with_nothing_to_resume_starts_a_new_conversation(cli_with, capsys):
    pipeline = cli_with([("welcome", True)], store=_Store(latest=None))

    cli.main(["--resume"])

    out = capsys.readouterr().out
    assert "No unfinished conversation to resume" in out
    assert pipeline.built["session_id"] is None
    assert pipeline.received == [""]


def test_an_unknown_session_id_is_started_under_that_id_and_says_so(cli_with, capsys):
    pipeline = cli_with([("welcome", True)], session_id="mine")

    cli.main(["--session", "mine"])

    out = capsys.readouterr().out
    assert "Could not resume 'mine'" in out
    assert pipeline.built["session_id"] == "mine"


def test_session_and_resume_together_are_rejected(cli_with, capsys):
    cli_with()

    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--session", "x", "--resume"])

    assert exit_info.value.code == 2
    assert "not allowed with" in capsys.readouterr().err


def test_a_database_from_a_newer_version_stops_with_a_clear_message(monkeypatch, capsys):
    def _refuse(path):
        raise SessionStoreError("uses session schema 99")

    monkeypatch.setattr(cli, "setup_logging", lambda: None)
    monkeypatch.setattr(cli, "SessionStore", _refuse)

    with pytest.raises(SystemExit) as exit_info:
        cli.main([])

    assert exit_info.value.code == 1
    assert "schema 99" in capsys.readouterr().err
