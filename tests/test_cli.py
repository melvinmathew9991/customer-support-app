import pytest

from customer_support_app import cli
from customer_support_app.domain.chat import Role
from customer_support_app.domain.graph import MessageOutput


class _Pipeline:
    """Replays scripted replies; the conversation ends when the script says so."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.received = []

    def run(self, user_input):
        self.received.append(user_input)
        message, is_over = self.replies.pop(0)
        return [MessageOutput(message, Role.ASSISTANT)], is_over


@pytest.fixture
def cli_with(monkeypatch):
    def _install(replies, typed):
        pipeline = _Pipeline(replies)
        typed = iter(typed)

        def _input():
            try:
                return next(typed)
            except StopIteration:
                raise EOFError

        monkeypatch.setattr(cli, "setup_logging", lambda: None)
        monkeypatch.setattr(cli, "CustomerSupportPipeline", lambda: pipeline)
        monkeypatch.setattr("builtins.input", _input)
        return pipeline

    return _install


def test_end_of_input_ends_the_session_cleanly(cli_with, capsys):
    pipeline = cli_with([("welcome", False)], typed=[])

    assert cli.main() is None

    assert capsys.readouterr().out.splitlines() == ["welcome", cli.GOODBYE]
    assert pipeline.received == [""]


@pytest.mark.parametrize("command", ["quit", "exit", "  Quit  ", "EXIT"])
def test_quit_and_exit_end_the_session_without_reaching_the_pipeline(cli_with, capsys, command):
    pipeline = cli_with([("welcome", False)], typed=[command])

    cli.main()

    assert capsys.readouterr().out.splitlines()[-1] == cli.GOODBYE
    assert pipeline.received == [""]


def test_a_normal_conversation_runs_to_its_own_end_without_a_goodbye(cli_with, capsys):
    pipeline = cli_with(
        [("welcome", False), ("hello", False), ("bye", True)], typed=["hi", "thanks"]
    )

    cli.main()

    assert capsys.readouterr().out.splitlines() == ["welcome", "hello", "bye"]
    assert pipeline.received == ["", "hi", "thanks"]
