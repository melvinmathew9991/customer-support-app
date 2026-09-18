import uuid
from typing import Optional, List, Tuple

from customer_support_app.agents.support import (
    UserInfoChainBasedEdge,
    AuthenticatedUserNode,
    GreetingNode,
    CallCustomerEdge,
    CallCustomerNode,
)
from customer_support_app.config import get_chat_model
from customer_support_app.domain.chat import MessageHistory, Role
from customer_support_app.domain.graph import MessageOutput, EdgeOutput
from customer_support_app.domain.validation import UserProfile, PhoneCallTicket
from customer_support_app.graph.node import BaseNode
from customer_support_app.logging_config import log_latency


class CustomerSupportPipeline:

    def __init__(self):
        self._llm_model = get_chat_model(temperature=0)
        self._message_history = MessageHistory([])
        self._current_node = None
        # Ties every turn-log record for this conversation together - see
        # docs/eval/Metrics.md for how the turn log feeds the eval harness.
        self._conversation_id = str(uuid.uuid4())

    def _get_pipeline(self) -> BaseNode:
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
            model=self._llm_model, pydantic_object=UserProfile, out_node=self._help_node
        )

        self._start_node = GreetingNode(edges=[self._user_info_chain])
        return self._start_node

    def _set_current_node(self, node: BaseNode) -> MessageOutput:
        self._current_node = node
        return node.greeting_message()

    def run(self, user_input: Optional[str]) -> Tuple[List[MessageOutput], bool]:
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
                greeting = self._set_current_node(self._get_pipeline())
                self._message_history.add_message(
                    content=greeting.message, role=greeting.role
                )
                turn_fields["node_after"] = type(self._current_node).__name__
                return [greeting], self._current_node.is_node_final()

            else:
                output = self._current_node.execute(self._message_history)
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
