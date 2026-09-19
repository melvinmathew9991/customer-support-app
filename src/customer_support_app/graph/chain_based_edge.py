import abc
from abc import ABC
from typing import Optional, Type, Union

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel

from customer_support_app.config import get_settings
from customer_support_app.domain.chat import MessageHistory, ModelInput
from customer_support_app.domain.graph import MessageOutput
from customer_support_app.graph.edge import BaseEdge
from customer_support_app.logging_config import log_latency


class ChainBasedEdge(BaseEdge[MessageHistory, MessageOutput], ABC):
    def __init__(
        self,
        model,
        pydantic_object: Optional[Type[BaseModel]],
        max_retries=3,
        out_node=None,
    ):
        super().__init__(model=model, max_retries=max_retries, out_node=out_node)
        self._parse_class = pydantic_object
        if pydantic_object is not None:
            self._output_parser = PydanticOutputParser(pydantic_object=pydantic_object)
        else:
            self._output_parser = None

        self._init_chain()

    @abc.abstractmethod
    def _predict(self, model_input: ModelInput) -> str:
        pass

    @abc.abstractmethod
    def _init_chain(self, *kwargs):
        pass

    def check(self, model_output: str) -> bool:
        return isinstance(self._output_parser.parse(model_output), BaseModel)

    def _parse(self, message_history: MessageHistory) -> Union[str, BaseModel]:
        model_input = message_history.model_input()
        str_to_parse = self._predict(model_input=model_input)
        out = (
            self._output_parser.parse(str_to_parse)
            if self._output_parser is not None
            else str_to_parse
        )
        return out


class ZeroShotChainBasedEdge(ChainBasedEdge, ABC):
    """A tool-using agent edge driven by a tool-calling capable chat model.

    Uses LangChain's provider-agnostic tool-calling agent, which works both
    with OpenAI models and with local tool-calling Ollama models (e.g.
    llama3.2), unlike the legacy OpenAI-functions-specific agent this used to
    wrap.

    Gathering information via tools and formatting the final structured
    answer are done as two separate LLM calls rather than asking the agent to
    do both in one pass. Smaller local models are unreliable at emitting a
    clean, schema-matching final answer in the same turn they're also doing
    tool-call reasoning - splitting the steps makes this far more robust.
    """

    _prompt_prefix = None
    _prompt_suffix = None

    def _get_agent_prompt_template(self) -> ChatPromptTemplate:
        system = self._prompt_prefix or ""
        if self._prompt_suffix:
            system += f"\n{self._prompt_suffix}"

        return ChatPromptTemplate.from_messages(
            [
                ("system", system),
                ("human", "Conversation history:\n{history}\n\n{input}"),
                MessagesPlaceholder("agent_scratchpad"),
            ]
        )

    def _init_chain(self, **kwargs):
        self._tools = self._get_tools()
        self._prompt = self._get_agent_prompt_template()

        agent = create_tool_calling_agent(self._llm_model, self._tools, self._prompt)
        self._agent_executor = AgentExecutor(
            agent=agent,
            tools=self._tools,
            verbose=get_settings().agent_verbose,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
        )

        # with_structured_output constrains generation to the target schema
        # (via the model's native tool/JSON-schema support) instead of asking
        # the model to freehand emit matching JSON text - far more reliable,
        # especially on smaller local models.
        self._structured_llm = (
            self._llm_model.with_structured_output(self._parse_class)
            if self._parse_class is not None
            else None
        )

    @abc.abstractmethod
    def _get_tools(self):
        pass

    def _gather_findings(self, model_input: ModelInput) -> str:
        with log_latency("tool_calling_agent", edge=type(self).__name__) as fields:
            result = self._agent_executor.invoke(
                {"input": model_input.input, "history": model_input.history}
            )
            fields["tool_calls"] = [
                {"tool": action.tool, "input": str(action.tool_input)}
                for action, _observation in result.get("intermediate_steps", [])
            ]

        # Exposed so subclasses can check *what argument* a tool was called
        # with, not just whether it returned something - a tool-calling
        # model can hallucinate a plausible argument (see
        # UserInfoChainBasedEdge._parse and docs/eval/Baseline-2026-09-19.md).
        self._last_intermediate_steps = result.get("intermediate_steps", [])

        findings = result["output"]

        # The agent's natural-language "final answer" is a lossy summary -
        # smaller models inconsistently restate every field they looked up.
        # Append the raw tool observations too, so nothing gets lost before
        # the structured-extraction step downstream.
        observations = "\n".join(
            f"- {action.tool} result: {observation}"
            for action, observation in result.get("intermediate_steps", [])
        )
        if observations:
            findings = f"{findings}\n\nRaw tool results:\n{observations}"

        return findings

    def _predict(self, model_input: ModelInput) -> str:
        return self._gather_findings(model_input)

    def _parse(self, message_history: MessageHistory) -> Union[str, BaseModel]:
        model_input = message_history.model_input()
        findings = self._gather_findings(model_input)

        if self._structured_llm is None:
            return findings

        return self._structured_llm.invoke(
            f"Extract the requested information from these findings:\n{findings}"
        )
