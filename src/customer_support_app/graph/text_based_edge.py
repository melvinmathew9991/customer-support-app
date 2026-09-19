from typing import Optional, Type, Union

from pydantic import BaseModel

from customer_support_app.domain.chat import MessageHistory, Role
from customer_support_app.domain.graph import MessageOutput
from customer_support_app.domain.validation import Validation
from customer_support_app.graph.edge import BaseEdge


class PydanticTextBasedEdge(BaseEdge[MessageHistory, MessageOutput]):

    """Edge
    at it's highest level, an edge checks if an input is good, then parses
    data out of that input if it is good
    """

    def __init__(
        self,
        condition: str,
        parse_prompt: str,
        parse_class: Type[BaseModel],
        llm_model,
        max_retries: Optional[int] = None,
        out_node=None,
    ):
        """
        condition (str): a True/False question about the input
        parse_query (str): what the parser whould be extracting
        parse_class (Pydantic BaseModel): the structure of the parse
        llm (LangChain LLM): the large language model being used
        """
        super().__init__(model=llm_model, max_retries=max_retries, out_node=out_node)
        self.condition = condition
        self.parse_prompt = parse_prompt
        self.parse_class = parse_class

        # with_structured_output constrains generation to the target schema
        # (via the model's native tool/JSON-schema support) instead of asking
        # the model to freehand emit matching JSON text - far more reliable,
        # especially on smaller local models, than manually building a
        # format-instructions prompt and regex-parsing the raw completion.
        self._validation_llm = llm_model.with_structured_output(Validation)
        self._extraction_llm = llm_model.with_structured_output(self.parse_class)

    def check(self, user_input: MessageHistory) -> bool:
        """ask the llm if the input satisfies the condition"""
        # System messages are internal bookkeeping (e.g. the retrieved user profile,
        # with its own phone number) - showing them to a small model biases the
        # yes/no answer, so only the user/assistant conversation is passed.
        history = "".join(
            f"\n{msg['role']}: {msg['content']}"
            for msg in user_input.messages[:-1]
            if msg["role"] != Role.SYSTEM
        )
        last_input = (user_input.role_based_history(Role.USER)[-1])["content"]

        try:
            result: Validation = self._validation_llm.invoke(
                "You are checking a single yes/no condition about the user's "
                "latest message below. Answer strictly based on what the "
                "message says or clearly implies - don't overthink it.\n"
                f"Conversation history:\n{history}\n"
                f"Condition: {self.condition}\n"
                f"User's latest message: {last_input}"
            )
            return result.is_valid
        except Exception:
            # A local model occasionally fails to produce valid structured
            # output - treat that as "condition not satisfied" rather than
            # crashing the whole conversation.
            return False

    def _parse(self, user_input: MessageHistory) -> Union[str, BaseModel]:
        """ask the llm to parse the parse_class, based on the parse_prompt, from the input"""
        return self._extraction_llm.invoke(f"{self.parse_prompt}:\n\nInput: {user_input}")

    def execute(self, user_input: MessageHistory):
        # input did't make it past the input condition for the edge
        if not self.check(user_input):
            self._num_fails += 1
            if self._max_retries is not None:
                if self._num_fails >= self._max_retries:
                    return self._get_edge_output(should_continue=True, result=None)
            return self._get_edge_output(should_continue=False, result=None)
        return super().execute(user_input)
