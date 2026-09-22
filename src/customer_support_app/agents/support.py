import logging
import random
import re
from typing import List, Optional, Type, Union

from langchain_core.exceptions import OutputParserException
from langchain_core.tools import Tool
from pydantic import BaseModel

from customer_support_app.domain.chat import MessageHistory, Role
from customer_support_app.domain.graph import MessageOutput
from customer_support_app.domain.validation import PhoneCallRequest, PhoneCallTicket, UserProfile
from customer_support_app.graph.chain_based_edge import ZeroShotChainBasedEdge
from customer_support_app.graph.chain_based_node import MultifunctionNode, RetrievalNode
from customer_support_app.graph.node import BaseEdge, BaseNode, NodeInput
from customer_support_app.graph.text_based_edge import PydanticTextBasedEdge
from customer_support_app.tools.audio_transcribe import call_customer, transcription_available
from customer_support_app.tools.rag_responder import HelpCenterAgent
from customer_support_app.tools.user_store import MockUserStore, UserStore

logger = logging.getLogger(__name__)

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

    def __init__(self, *args, user_store: Optional[UserStore] = None, **kwargs):
        # Set before super().__init__(), which calls _init_chain() -> _get_tools() below.
        self._user_store = user_store if user_store is not None else MockUserStore()
        super().__init__(*args, **kwargs)

    def _get_tools(self):
        tools = [
            Tool.from_function(
                func=self._user_store.search_user_info,
                description=(
                    "Database tool to search user information. "
                    "Input must be the user's email address or phone number exactly as "
                    "they gave it, e.g. 'john@doe.com' or '0452 333 667'. "
                    "The result includes a numeric 'user_id' field to use with "
                    "user_subscription_db_search."
                ),
                name="user_info_db_search",
            ),
            Tool.from_function(
                func=self._user_store.search_user_subscription,
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

    @staticmethod
    def _tool_call_input(intermediate_steps, tool_name: str) -> Optional[str]:
        for action, _observation in intermediate_steps:
            if action.tool == tool_name:
                tool_input = action.tool_input
                if isinstance(tool_input, dict):
                    # some tool-calling models wrap the single positional arg
                    # in a dict (e.g. {"email": "..."}) rather than passing it
                    # bare - unwrap to the first value either way.
                    tool_input = next(iter(tool_input.values()), None)
                return str(tool_input) if tool_input is not None else None
        return None

    @staticmethod
    def _appears_in(value: str, message: str) -> bool:
        """True if the looked-up value is in the user's own message, ignoring case and, for
        phone numbers, spacing and punctuation."""
        value, message = value.strip().lower(), message.lower()
        if value in message:
            return True
        digits = re.sub(r"\D", "", value)
        return len(digits) >= 6 and digits in re.sub(r"\D", "", message)

    @staticmethod
    def _observed_record(intermediate_steps, tool_name: str) -> Optional[dict]:
        """The first record a tool actually returned, or None if it returned none."""
        for action, observation in intermediate_steps:
            if action.tool == tool_name and isinstance(observation, list) and observation:
                if isinstance(observation[0], dict):
                    return observation[0]
        return None

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
        # A model can skip the second tool call (llama3.1:8b writes it out as text
        # instead of calling it), leaving no subscription in the findings. The
        # extractor would then invent one, so a missing lookup must fail like an
        # empty one. See the larger-model experiment results.
        if "user_subscription_db_search result:" not in findings:
            raise OutputParserException(
                "The subscription lookup never ran - can't determine the user's tier."
            )
        if self._NO_SUBSCRIPTION_MATCH.search(findings):
            raise OutputParserException(
                "The user was found but has no subscription record - can't determine their tier."
            )

        # A real match from the DB tool isn't enough on its own - the tool
        # call's own argument is model-generated and can be fabricated
        # rather than taken from what the user actually typed (confirmed:
        # given input as unrelated as "what's up", the agent called
        # user_info_db_search with "john@doe.com" - a real account, but one
        # the user never provided. See docs/eval/Baseline-2026-09-19.md).
        # Require the looked-up value to actually appear in the user's own
        # latest message before trusting the match.
        last_user_message = message_history.role_based_history(Role.USER)[-1]["content"]
        lookup_value = self._tool_call_input(
            getattr(self, "_last_intermediate_steps", []), "user_info_db_search"
        )
        if not lookup_value or not self._appears_in(lookup_value, last_user_message):
            raise OutputParserException(
                "The user lookup was performed with a value that doesn't appear in the "
                "user's own message - refusing to trust a fabricated identity."
            )

        # The tier decides which KB the user is served, so it comes from the DB
        # record itself, never from the extractor's reading of the findings, and
        # only if that record belongs to the user who was identified.
        steps = getattr(self, "_last_intermediate_steps", [])
        user_record = self._observed_record(steps, "user_info_db_search")
        subscription_record = self._observed_record(steps, "user_subscription_db_search")
        if (
            user_record is None
            or subscription_record is None
            or str(user_record.get("user_id")) != str(subscription_record.get("user_id"))
        ):
            raise OutputParserException(
                "The subscription record doesn't belong to the user that was looked up."
            )

        profile = self._structured_llm.invoke(
            f"Extract the requested information from these findings:\n{findings}"
        )
        return profile.model_copy(update={"subscription": subscription_record["subscription"]})


class AuthenticatedUserNode(RetrievalNode):
    STATIC_PROMPT = [
        "Hi, {user_name} I am your Shopify Agent for today, you have the "
        "{subscription} subscription "
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

    def is_node_final(self) -> bool:
        # Without a UserProfile identification failed, and the fail-safe message in
        # greeting_message() is the last thing the user is told: the conversation ends there
        # instead of carrying on with the free KB for someone who was never identified (#37).
        return not isinstance(self._node_input, UserProfile)

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
                "Does the user ask a support agent to call them? Only mentioning, "
                "giving, changing or asking about a phone number is not a request "
                "to be called."
            ),
            parse_prompt="Extract the phone number from the user message",
            parse_class=PhoneCallRequest,
            llm_model=llm_model,
            max_retries=max_retries,
            out_node=out_node,
        )

    # At least 6 digits, allowing spaces/dashes/brackets between them.
    _PHONE_NUMBER_RE = re.compile(r"(?:\d[\s\-().]*){6,}")

    # Unambiguous ways of asking to be called, and of asking not to be. The 3B model
    # misses some plain requests ("Can you call me?") once a number is present and
    # accepts non-requests that merely mention one, so these are decided without it.
    _CALL_ME_RE = re.compile(
        r"\b(?:call|ring|phone)\s+me\b|\bgive\s+me\s+a\s+(?:call|ring)\b|\bcall\s*back\b"
        r"|\bcall\s+(?:this|that|the)\s+number\b"
        r"|\b(?:someone|somebody|an?\s+agent)\s+(?:to\s+|could\s+|can\s+|should\s+)?"
        r"(?:call|phone|ring)\b",
        re.IGNORECASE,
    )
    _DO_NOT_CALL_RE = re.compile(
        r"\b(?:don'?t|do\s+not|not|never|no)\s+(?:to\s+)?(?:call|phone|ring)\b|\bno\s+calls?\b"
        r"|\bno\s+need\s+(?:to\s+|for\s+(?:you\s+to\s+|a\s+)?)?(?:call|phone|ring)\b",
        re.IGNORECASE,
    )

    def check(self, user_input: MessageHistory) -> bool:
        # A callback request always names the number to call. Requiring one is
        # deterministic, and keeps questions that merely mention phones or how to
        # reach support (which the 3B model conflates with callback requests)
        # from ever reaching the LLM-based intent check.
        last_input = user_input.role_based_history(Role.USER)[-1]["content"]
        if not self._PHONE_NUMBER_RE.search(last_input):
            return False
        # A decline only cancels the request it is part of, so it is taken out before looking
        # for one: "never call me on X" has nothing left, while "never call me before 9am, but
        # do call me on X" still has its second request (#33).
        without_declines, declines = self._DO_NOT_CALL_RE.subn(" ", last_input)
        if self._CALL_ME_RE.search(without_declines):
            return True
        if declines:
            return False
        return super().check(user_input)

    # A whole number as typed (optional leading + or bracket), for reading it back.
    _PHONE_NUMBER_SPAN_RE = re.compile(r"\+?\(?\d(?:[\s\-().]*\d){5,}")

    def _parse(self, user_input: MessageHistory) -> Union[str, BaseModel]:
        result = super()._parse(user_input)
        # Never call a number the user did not type: the extracted digits must
        # appear in their own latest message.
        last_input = user_input.role_based_history(Role.USER)[-1]["content"]
        extracted = re.sub(r"\D", "", result.phone_number)
        if extracted and extracted in re.sub(r"\D", "", last_input):
            return result
        # The 3B model sometimes mis-copies a digit. If the message holds exactly
        # one number, that number is the one to call; with several, rejecting
        # falls through to the normal answer path rather than guessing.
        typed = self._PHONE_NUMBER_SPAN_RE.findall(last_input)
        if len(typed) == 1:
            return PhoneCallRequest(phone_number=typed[0].strip())
        raise OutputParserException(
            "The extracted phone number does not appear in the user's message."
        )

    def _get_message_output(
        self, msg_input: Union[str, BaseModel]
    ) -> Optional[List[MessageOutput]]:
        if isinstance(msg_input, PhoneCallRequest):
            system_message = MessageOutput(
                "User has been called as per their request", Role.SYSTEM
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
        if not transcription_available():
            return self._callback_logged_message()

        message_history = MessageHistory(messages=[])
        message_history.add_user_message(
            content=f"Call user on his phone number: {self._node_input.phone_number}"
        )

        completion = self._predict(message_history)
        if self._output_parser is not None:
            try:
                ticket_request: PhoneCallTicket = self._output_parser.parse(completion)
            except OutputParserException:
                # A ticket the model got wrong must not end the conversation: the callback
                # is still logged, only the summary is missing (#43).
                logger.warning("Could not read a ticket from the call tool", exc_info=True)
                return self._callback_logged_message()
            return MessageOutput(
                message="We are connecting you to our customer care representative Ruby.  "
                "We will be happy to resolve your queries via call."
                f"\n"
                f"\n"
                f"\n"
                f"\n"
                f"\n"
                f"\n"
                f"\nThanks for your time today with {ticket_request.agent_name}  "
                f"a ticket has been created on your behalf"
                f"\nHere is your ticket summary: "
                f"\n\n{ticket_request.call_summary}"
                f"\n\nThanks for your time today! See you next time. "
                f"We are closing this ticket now.",
                role=Role.ASSISTANT,
            )
        return None

    def _callback_logged_message(self) -> MessageOutput:
        # Without the optional `audio` extra there is no call to transcribe, so
        # no ticket summary can be produced - say so instead of inventing one.
        return MessageOutput(
            message=f"We've logged your callback request for {self._node_input.phone_number}. "
            f"A customer care representative will call you back shortly.",
            role=Role.ASSISTANT,
        )

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
