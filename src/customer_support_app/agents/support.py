import random
import re
from typing import Optional, Type, Union, List

from langchain_core.exceptions import OutputParserException
from langchain_core.tools import Tool
from pydantic import BaseModel

from customer_support_app.domain.chat import MessageHistory, Role
from customer_support_app.domain.graph import MessageOutput
from customer_support_app.domain.validation import UserProfile, PhoneCallRequest, PhoneCallTicket
from customer_support_app.graph.chain_based_edge import ZeroShotChainBasedEdge
from customer_support_app.graph.chain_based_node import RetrievalNode, MultifunctionNode
from customer_support_app.graph.node import BaseNode, BaseEdge, NodeInput
from customer_support_app.graph.text_based_edge import PydanticTextBasedEdge
from customer_support_app.tools.audio_transcribe import call_customer
from customer_support_app.tools.rag_responder import HelpCenterAgent
from customer_support_app.tools.user_info_db import (
    search_user_info_on_db,
    search_user_subscription_on_db,
)

PREMIUM_SUBSCRIPTIONS = {"premium", "pro"}


class GreetingNode(BaseNode[str]):
    STATIC_PROMPT = [
        "Hi, welcome to our online support, in order to proceed we need to identify you first, "
        "could you please input your full email address or phone number"
    ]
    RETRY_PROMPT = [
        "I'm sorry, I didn't understand your response."
        "\nPlease provide a full email address or phone number(in the format xxx-xxx-xxxx)"
    ]

    def greeting_message(self) -> Optional[MessageOutput]:
        prompt = random.choice(self.STATIC_PROMPT)
        return MessageOutput(prompt, role=Role.ASSISTANT)

    def no_edges_found(self, user_input: str) -> Optional[MessageOutput]:
        prompt = random.choice(self.RETRY_PROMPT)
        return MessageOutput(prompt, role=Role.ASSISTANT)


class UserInfoChainBasedEdge(ZeroShotChainBasedEdge):
    _prompt_prefix = """Your goal is to find out the user information and their subscription type.

Follow these steps in order:
1. Call user_info_db_search with the email or phone number the user gave you. This returns a
   record containing a "user_id" field (a number).
2. Call user_subscription_db_search using THAT NUMERIC "user_id" from step 1 as the input -
   never the user's email or phone number. Subscriptions are looked up by user_id only.
3. Combine both results into your final answer. The subscription must be either free or
   premium, never empty.

To achieve this you have access to the following tools:"""

    _prompt_suffix = (
        "Your final answer should combine the information of previous tool observations."
    )

    def _get_tools(self):
        tools = [
            Tool.from_function(
                func=search_user_info_on_db,
                description=(
                    "Database tool to search user information. "
                    "Input must be the user's email address as text, e.g. 'john@doe.com'. "
                    "The result includes a numeric 'user_id' field to use with "
                    "user_subscription_db_search."
                ),
                name="user_info_db_search",
            ),
            Tool.from_function(
                func=search_user_subscription_on_db,
                description=(
                    "Database tool to search a user's subscription type. "
                    "Input must be the numeric 'user_id' returned by user_info_db_search, "
                    "e.g. '1' - never an email address or phone number."
                ),
                name="user_subscription_db_search",
            ),
        ]
        return tools

    def _get_message_output(
        self, msg_input: Union[str, BaseModel]
    ) -> List[MessageOutput]:
        user_info = msg_input if isinstance(msg_input, str) else str(msg_input)
        message = f"User Info retrieved: {user_info}"
        return [MessageOutput(message, Role.SYSTEM)]

    # with_structured_output constrains the *shape* of the extraction
    # result, but nothing stops the model from inventing plausible-looking
    # values (a blank name, a name guessed from the email, "free" as a
    # default subscription) for a schema whose fields are all required.
    # Confirmed via the Sprint 1 golden set (ident-003/ident-004/ident-005 in
    # tests/eval/golden_set.json): unrelated input, and even a genuinely
    # unknown email, both produced a fabricated-but-schema-valid UserProfile
    # instead of failing - i.e. a silent identity bypass. _gather_findings
    # always embeds the raw tool observation as
    # "- <tool_name> result: <observation>", so we can check deterministically
    # whether the lookup tools actually found something before ever asking
    # the model to extract a UserProfile from the findings.
    _NO_USER_MATCH = re.compile(r"user_info_db_search result:\s*\[\s*\]")
    _NO_SUBSCRIPTION_MATCH = re.compile(r"user_subscription_db_search result:\s*\[\s*\]")

    def _parse(self, message_history: MessageHistory) -> Union[str, BaseModel]:
        model_input = message_history.model_input()
        findings = self._gather_findings(model_input)

        if "user_info_db_search result:" not in findings:
            raise OutputParserException(
                "No email or phone number was found in the user's message to look up."
            )
        if self._NO_USER_MATCH.search(findings):
            raise OutputParserException(
                "No user record matches the email or phone number provided."
            )
        if self._NO_SUBSCRIPTION_MATCH.search(findings):
            raise OutputParserException(
                "The user was found but has no subscription record - can't determine their tier."
            )

        return self._structured_llm.invoke(
            f"Extract the requested information from these findings:\n{findings}"
        )


class AuthenticatedUserNode(RetrievalNode):
    STATIC_PROMPT = [
        "Hi, {user_name} I am your Shopify Agent for today, you have the {subscription} subscription "
        "I can help you with any Help or you can ask me to call you at anytime!"
    ]

    def __init__(
        self,
        llm_model,
        pydantic_object: Optional[Type[BaseNode]],
        edges: List[BaseEdge] = None,
    ):
        self._hc_agent = HelpCenterAgent()
        super().__init__(llm_model, pydantic_object, edges)

    def greeting_message(self) -> Optional[MessageOutput]:
        user_profile = self._node_input
        if not isinstance(user_profile, UserProfile):
            # UserInfoChainBasedEdge exhausted its retries (e.g. the user
            # never provided an identifiable email/phone, or gave one with
            # no matching record) and handed this node an error payload
            # instead of a real UserProfile. Fail safe with a plain message
            # rather than crashing on user_profile.name below.
            return MessageOutput(
                "Sorry, we still couldn't verify your account. Please refresh and start "
                "again with your registered email address or phone number.",
                role=Role.ASSISTANT,
            )

        prompt = random.choice(self.STATIC_PROMPT)
        prompt = prompt.format(
            user_name=user_profile.name, subscription=user_profile.subscription
        )
        return MessageOutput(prompt, role=Role.ASSISTANT)

    def _get_retriever(self):
        # Deterministically pick the knowledge base for the user's own tier,
        # instead of asking the LLM to guess which KB a question belongs to
        # (which could leak premium content to free users or vice versa).
        user_profile = self._node_input
        if (
            isinstance(user_profile, UserProfile)
            and user_profile.subscription.lower() in PREMIUM_SUBSCRIPTIONS
        ):
            return self._hc_agent.paid_sub_retriever()
        return self._hc_agent.free_sub_retriever()

    def no_edges_found(self, user_input: MessageHistory) -> Optional[MessageOutput]:
        message = self._predict(user_input)
        return MessageOutput(message=message, role=Role.ASSISTANT)


class CallCustomerEdge(PydanticTextBasedEdge):
    def __init__(self, llm_model, max_retries: int = 5, out_node: BaseNode = None):
        super().__init__(
            condition=(
                "Is the user asking to be called, phoned, or rung back on a phone "
                "number (e.g. 'call me', 'please call me back', 'can you ring me at ...')?"
            ),
            parse_prompt="Extract the phone number from the user message",
            parse_class=PhoneCallRequest,
            llm_model=llm_model,
            max_retries=max_retries,
            out_node=out_node,
        )

    def _get_message_output(
        self, msg_input: Union[str, BaseModel]
    ) -> Optional[List[MessageOutput]]:
        if isinstance(msg_input, PhoneCallRequest):
            system_message = MessageOutput(
                f"User has been called as per their request", Role.SYSTEM
            )

            assistant_message = MessageOutput(
                f"Sure we are calling you now on: {msg_input.phone_number}",
                Role.ASSISTANT,
            )
            return [system_message, assistant_message]
        else:
            return None


class CallCustomerNode(MultifunctionNode):
    def greeting_message(self) -> Optional[MessageOutput]:
        message_history = MessageHistory(messages=[])
        message_history.add_user_message(
            content=f"Call user on his phone number: {self._node_input.phone_number}"
        )

        completion = self._predict(message_history)
        if self._output_parser is not None:
            ticket_request: PhoneCallTicket = self._output_parser.parse(completion)
            return MessageOutput(
                message=f"We are connecting you to our customer care representative Ruby.  We will be happy to resolve your queries via call."
                f"\n"
                f"\n"
                f"\n"
                f"\n"
                f"\n"
                f"\n"
                f"\nThanks for your time today with {ticket_request.agent_name}  a ticket has been created on your behalf"
                f"\nHere is your ticket summary: "
                f"\n\n{ticket_request.call_summary}"
                f"\n\nThanks for your time today! See you next time. We are closing this ticket now.",
                role=Role.ASSISTANT,
            )
        return None

    def no_edges_found(self, user_input: NodeInput) -> Optional[MessageOutput]:
        return None

    def _get_tools(self):
        tools = [
            Tool.from_function(
                func=call_customer,
                description="Use to call premium customers",
                name="call_customer_tool",
                return_direct=True,
            )
        ]
        return tools
