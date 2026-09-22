"""Logging setup for entrypoints (CLI, Streamlit app).

Library modules should never call logging.basicConfig themselves - only an
entrypoint should configure the root logger, so importing this package as a
dependency doesn't clobber a host application's own logging setup.

This also sets up a second, structured logger (TURN_LOGGER_NAME) that
writes one JSON-line record per notable event - a turn, a retrieval call,
a tool-calling agent invocation - to a separate file. This is the raw
per-turn data Sprint 1's eval harness depends on (current node, retrieved
doc ids + scores, tool calls made, latency); see docs/eval/Metrics.md for
how each field feeds a specific metric. It's deliberately kept separate
from the human-readable console logger so it stays machine-parseable
regardless of LOG_LEVEL/console formatting.
"""
import json
import logging
import time
from contextlib import contextmanager

from langchain_core.callbacks import BaseCallbackHandler

from customer_support_app.config import get_settings

TURN_LOGGER_NAME = "customer_support_app.turns"


class _JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "event": record.getMessage(),
        }
        payload.update(getattr(record, "turn_fields", {}))
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    turn_logger = logging.getLogger(TURN_LOGGER_NAME)
    turn_logger.setLevel(logging.INFO)
    # Keep structured lines out of the human-readable console stream and
    # out of any host application's own root-logger handlers.
    turn_logger.propagate = False
    turn_logger.handlers = []

    log_path = settings.turn_log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(_JsonLineFormatter())
    turn_logger.addHandler(handler)


def log_turn_event(event: str, **fields) -> None:
    """Emit one structured JSON-line record to the turn log."""
    logging.getLogger(TURN_LOGGER_NAME).info(event, extra={"turn_fields": fields})


@contextmanager
def log_latency(event: str, **fields):
    """Times the wrapped block and emits one turn-log record on exit.

    Usage:
        with log_latency("retrieval", query=q) as f:
            f["retrieved_docs"] = [...]  # add more fields before it logs

    `latency_ms` is added automatically. Logs even if the wrapped block
    raises, so a failed call still shows up in the turn log.
    """
    start = time.perf_counter()
    try:
        yield fields
    finally:
        fields["latency_ms"] = round((time.perf_counter() - start) * 1000, 1)
        log_turn_event(event, **fields)


class TokenUsageCallbackHandler(BaseCallbackHandler):
    """Logs input/output token counts for every LLM call as a turn-log event.

    Attached at the chat-model instance level in config.get_chat_model(), so it fires
    for every call that instance makes - including calls nested inside an
    AgentExecutor or a retrieval chain - the same way log_latency already captures
    retrieval and tool-calling-agent latency, without having to instrument every
    call site individually. Relies on langchain_core's standardized
    AIMessage.usage_metadata, which both langchain_ollama and langchain_openai
    populate (prompt_eval_count/eval_count and OpenAI's usage field, respectively).
    """

    def __init__(self, provider: str, model: str):
        self._provider = provider
        self._model = model

    def on_llm_end(self, response, **kwargs) -> None:
        for generation_list in response.generations:
            for generation in generation_list:
                usage = getattr(getattr(generation, "message", None), "usage_metadata", None)
                if not usage:
                    continue
                log_turn_event(
                    "llm_usage",
                    provider=self._provider,
                    model=self._model,
                    input_tokens=usage.get("input_tokens"),
                    output_tokens=usage.get("output_tokens"),
                    total_tokens=usage.get("total_tokens"),
                )
