import abc

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel
from typing import Type, Optional, List

from customer_support_app.config import get_settings
from customer_support_app.domain.chat import MessageHistory, Role
from customer_support_app.graph.node import BaseNode
from customer_support_app.graph.edge import BaseEdge


class ChainBasedNode(BaseNode[MessageHistory], abc.ABC):
    def __init__(
        self,
        llm_model,
        pydantic_object: Optional[Type[BaseModel]],
        edges: Optional[List[BaseEdge]],
        final_state=False,
    ):
        self._llm_model = llm_model
        self._parse_class = pydantic_object

        if pydantic_object is not None:
            self._output_parser = PydanticOutputParser(pydantic_object=pydantic_object)
        else:
            self._output_parser = None

        self._init_chain()
        super().__init__(edges, final_state)

    @abc.abstractmethod
    def _init_chain(self, **kwargs):
        pass


class RetrievalNode(ChainBasedNode, abc.ABC):
    """A node that answers questions using a single retriever chosen for the
    current conversation (e.g. based on the authenticated user's tier),
    rather than having the LLM guess which knowledge base to search.
    """

    _SYSTEM_PROMPT = (
        "You are a helpful customer support assistant. Answer the question "
        "using only the context below. If the answer isn't contained in the "
        "context, say so politely instead of guessing.\n\nContext:\n{context}"
    )

    @abc.abstractmethod
    def _get_retriever(self):
        """Return the retriever to use for the current node input."""

    def _init_chain(self, *kwargs):
        prompt = ChatPromptTemplate.from_messages(
            [("system", self._SYSTEM_PROMPT), ("human", "{input}")]
        )
        self._combine_docs_chain = create_stuff_documents_chain(self._llm_model, prompt)

    def _predict(self, messages: MessageHistory) -> str:
        last_user_message = messages.role_based_history(role=Role.USER)[-1]["content"]
        retriever = self._get_retriever()
        chain = create_retrieval_chain(retriever, self._combine_docs_chain)
        result = chain.invoke({"input": last_user_message})
        return result["answer"]


class MultifunctionNode(ChainBasedNode, abc.ABC):
    def _init_chain(self, *kwargs):
        self._tools = self._get_tools()

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are a helpful assistant."),
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad"),
            ]
        )
        agent = create_tool_calling_agent(self._llm_model, self._tools, prompt)
        self._agent_executor = AgentExecutor(
            agent=agent,
            tools=self._tools,
            verbose=get_settings().agent_verbose,
            handle_parsing_errors=True,
        )

    @abc.abstractmethod
    def _get_tools(self):
        pass

    def _predict(self, messages: MessageHistory) -> str:
        completion = self._agent_executor.invoke({"input": str(messages)})
        return completion["output"]
