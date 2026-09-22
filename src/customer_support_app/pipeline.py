import logging
import sqlite3
import uuid
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pydantic import BaseModel

from customer_support_app.agents.support import (
    AuthenticatedUserNode,
    CallCustomerEdge,
    CallCustomerNode,
    GreetingNode,
    UserInfoChainBasedEdge,
)
from customer_support_app.config import get_chat_model, get_user_store
from customer_support_app.domain.chat import MessageHistory, Role
from customer_support_app.domain.graph import EdgeOutput, MessageOutput
from customer_support_app.domain.validation import PhoneCallRequest, PhoneCallTicket, UserProfile
from customer_support_app.graph.node import BaseNode
from customer_support_app.logging_config import log_latency
from customer_support_app.session_store import SessionRecord, SessionStore

logger = logging.getLogger(__name__)

TIMEOUT_REPLY = "Sorry, that took too long to answer. Please try again."

# What a node must have been handed for a saved session to be resumed at it. A session whose
# identification failed sits at AuthenticatedUserNode holding an error message instead of a
# UserProfile; it is not resumed, since the user was told to start again.
_RESUMABLE_INPUT = {
    "GreetingNode": type(None),
    "AuthenticatedUserNode": UserProfile,
    "CallCustomerNode": PhoneCallRequest,
}
_INPUT_MODELS: Dict[str, type] = {"UserProfile": UserProfile, "PhoneCallRequest": PhoneCallRequest}


def _dump_node_input(value: Any) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if isinstance(value, BaseModel):
        return {"type": type(value).__name__, "data": value.model_dump()}
    if isinstance(value, MessageOutput):
        data = {"message": value.message, "role": str(value.role)}
        return {"type": "MessageOutput", "data": data}
    raise TypeError(f"cannot save a node input of type {type(value).__name__}")


def _load_node_input(saved: Optional[Dict[str, Any]]) -> Any:
    if saved is None:
        return None
    kind, data = saved["type"], saved["data"]
    if kind == "MessageOutput":
        return MessageOutput(message=str(data["message"]), role=Role(data["role"]))
    return _INPUT_MODELS[kind].model_validate(data)


class CustomerSupportPipeline:
    """Runs one support conversation.

    Give it a `store` to have the conversation saved after every turn, and a `session_id`
    that the store already holds to pick that conversation up where it stopped
    (docs/Persistence-Design.md). With no store it keeps everything in memory, as before.
    """

    def __init__(self, store: Optional[SessionStore] = None, session_id: Optional[str] = None):
        self._llm_model = get_chat_model(temperature=0)
        self._message_history = MessageHistory([])
        self._current_node = None
        self._start_node = None
        # Ties every turn-log record for this conversation together - see
        # docs/eval/Metrics.md for how the turn log feeds the eval harness.
        self._conversation_id = str(uuid.uuid4())
        self._store = store
        self.session_id = session_id or (uuid.uuid4().hex if store is not None else None)
        # True when this pipeline was restored from a saved session rather than started new.
        self.resumed = False
        if store is not None and session_id is not None:
            self._resume(store.load(session_id))

    def _get_pipeline(self) -> BaseNode:
        # Resolved here, not in __init__: tests that monkeypatch this whole method (the
        # fake_graph fixture) never touch the real, on-disk store, the same way a bare
        # CustomerSupportPipeline() never touches the real LLM provider unless it actually
        # runs a turn.
        self._user_store = get_user_store()
        self._call_customer_node = CallCustomerNode(
            llm_model=self._llm_model,
            pydantic_object=PhoneCallTicket,
            edges=[],
            final_state=True,
        )
        self._call_customer_edge = CallCustomerEdge(
            llm_model=self._llm_model, out_node=self._call_customer_node
        )

        self._help_node = AuthenticatedUserNode(
            llm_model=self._llm_model,
            pydantic_object=None,
            edges=[self._call_customer_edge],
        )

        self._user_info_chain = UserInfoChainBasedEdge(
            model=self._llm_model,
            pydantic_object=UserProfile,
            out_node=self._help_node,
            user_store=self._user_store,
        )

        self._start_node = GreetingNode(edges=[self._user_info_chain])
        return self._start_node

    def _edges(self) -> Dict[str, Any]:
        return {
            "UserInfoChainBasedEdge": self._user_info_chain,
            "CallCustomerEdge": self._call_customer_edge,
        }

    def _nodes(self) -> Dict[str, BaseNode]:
        return {
            "GreetingNode": self._start_node,
            "AuthenticatedUserNode": self._help_node,
            "CallCustomerNode": self._call_customer_node,
        }

    def _resume(self, record: Optional[SessionRecord]) -> None:
        """Puts the conversation back at the node the record was saved at.

        Rebuilds the graph and sets its state; nothing is replayed and no model is called.
        A record that cannot be resumed leaves this a new conversation.
        """
        if record is None:
            return
        try:
            self._get_pipeline()
            node = self._nodes().get(record.node)
            if node is None:
                raise ValueError(f"unknown node {record.node!r}")
            node_input = _load_node_input(record.node_input)
            if not isinstance(node_input, _RESUMABLE_INPUT[record.node]):
                raise ValueError(f"{record.node} was saved without a usable input")
            edges = self._edges()
            fails = {name: record.edge_fails.get(name, 0) for name in edges}
            if not all(isinstance(n, int) and n >= 0 for n in fails.values()):
                raise ValueError("retry counters are not non-negative integers")
        except (ValueError, TypeError, KeyError) as error:
            logger.warning(
                "Starting a new conversation: session %s cannot be resumed: %s",
                record.session_id,
                error,
            )
            return
        node.set_node_input(node_input)
        for name, edge in edges.items():
            edge._num_fails = fails[name]
        self._current_node = node
        self._message_history = MessageHistory(list(record.messages))
        self._conversation_id = record.conversation_id
        self.resumed = True

    @property
    def ended(self) -> bool:
        return self._current_node is not None and self._current_node.is_node_final()

    @property
    def current_user_profile(self) -> Optional[UserProfile]:
        """The identified user, once AuthenticatedUserNode holds one - None before
        identification, or if it failed (see AuthenticatedUserNode.is_node_final)."""
        node_input = self._current_node._node_input if self._current_node else None
        return node_input if isinstance(node_input, UserProfile) else None

    def transcript(self) -> List[Dict[str, str]]:
        """What the user saw and typed so far (internal system lines left out)."""
        shown = (str(Role.USER), str(Role.ASSISTANT))
        return [dict(m) for m in self._message_history.messages if m["role"] in shown]

    def _save(self) -> None:
        if self._store is None or self._current_node is None:
            return
        try:
            self._store.save(
                SessionRecord(
                    session_id=self.session_id,
                    conversation_id=self._conversation_id,
                    node=type(self._current_node).__name__,
                    node_input=_dump_node_input(self._current_node._node_input),
                    edge_fails={name: edge._num_fails for name, edge in self._edges().items()},
                    messages=list(self._message_history.messages),
                    is_over=self._current_node.is_node_final(),
                )
            )
        except (sqlite3.Error, OSError, TypeError):
            # A failing save costs resumability, not the conversation in progress.
            logger.warning("Could not save session %s", self.session_id, exc_info=True)

    def _set_current_node(self, node: BaseNode) -> MessageOutput:
        self._current_node = node
        return node.greeting_message()

    def run(self, user_input: Optional[str]) -> Tuple[List[MessageOutput], bool]:
        result = self._run_turn(user_input)
        self._save()
        return result

    def _run_turn(self, user_input: Optional[str]) -> Tuple[List[MessageOutput], bool]:
        if user_input is not None and user_input != "":
            self._message_history.add_user_message(content=user_input)

        assistant_output: List[MessageOutput] = []
        node_before = type(self._current_node).__name__ if self._current_node else None

        with log_latency(
            "turn",
            conversation_id=self._conversation_id,
            node_before=node_before,
            user_input=user_input,
        ) as turn_fields:
            if self._current_node is None:
                greeting = self._set_current_node(self._start_node or self._get_pipeline())
                self._message_history.add_message(
                    content=greeting.message, role=greeting.role
                )
                turn_fields["node_after"] = type(self._current_node).__name__
                return [greeting], self._current_node.is_node_final()

            else:
                try:
                    output = self._current_node.execute(self._message_history)
                except httpx.TimeoutException:
                    # The model did not answer within LLM_TIMEOUT_SECONDS. Stay on the same
                    # node so the user can simply ask again, instead of crashing the session.
                    logger.warning("LLM call timed out on %s", node_before, exc_info=True)
                    turn_fields["timed_out"] = True
                    turn_fields["node_after"] = type(self._current_node).__name__
                    self._message_history.add_assistant_message(content=TIMEOUT_REPLY)
                    return (
                        [MessageOutput(TIMEOUT_REPLY, role=Role.ASSISTANT)],
                        self._current_node.is_node_final(),
                    )
                if isinstance(output, EdgeOutput):
                    if output.message_output is not None:
                        for msg_output in output.message_output:
                            self._message_history.add_message(
                                content=msg_output.message, role=msg_output.role
                            )
                            if msg_output.role == Role.ASSISTANT:
                                assistant_output.append(msg_output)

                    if output.next_node is not None:
                        node_output = self._set_current_node(output.next_node)
                        if isinstance(node_output, MessageOutput):
                            self._message_history.add_assistant_message(
                                content=node_output.message
                            )

                        if node_output.role == Role.ASSISTANT:
                            assistant_output.append(node_output)

                elif isinstance(output, MessageOutput):
                    self._message_history.add_message(content=output.message, role=output.role)
                    if output.role == Role.ASSISTANT:
                        assistant_output.append(output)

                turn_fields["node_after"] = type(self._current_node).__name__
                return assistant_output, self._current_node.is_node_final()
