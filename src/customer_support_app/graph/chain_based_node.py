import abc
import re
from pathlib import Path

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel
from typing import Type, Optional, List

from customer_support_app.config import PROJECT_ROOT, get_settings
from customer_support_app.domain.chat import MessageHistory, Role
from customer_support_app.graph.node import BaseNode
from customer_support_app.graph.edge import BaseEdge
from customer_support_app.logging_config import log_latency


NOT_COVERED_REPLY = "I don't have information about that in our help center."

# Navigation wording that shows up when a model describes an admin UI from general
# knowledge ("go to Settings > Payments and click Edit"). The knowledge base contains
# none of it, so if an answer uses it and the retrieved context does not, the steps
# were invented. Heuristic: it catches this pattern, not every kind of fabrication.
_NAVIGATION_MARKERS = (
    re.compile(r"\bclick(?:s|ed|ing)?\b", re.I),
    re.compile(r"\bnavigat\w*", re.I),
    re.compile(r"\btap(?:s|ped|ping)?\b", re.I),
    re.compile(r"\w\s*>\s*\w"),
)


def invents_steps(answer: str, context: str) -> bool:
    """True if the answer gives UI navigation the retrieved context never uses."""
    return any(m.search(answer) and not m.search(context) for m in _NAVIGATION_MARKERS)


def _relative_source(source: Optional[str]) -> Optional[str]:
    """Normalizes a Chroma doc's absolute source path to project-relative,
    e.g. "assets/free/pos.txt" - matching the format golden_set.json's
    expected_source_files use, so the two can be compared directly once
    the eval harness exists.
    """
    if not source:
        return source
    try:
        return Path(source).resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return source


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

    # Rules 3 and 5 exist because the 3B model answers uncovered questions, and
    # "how do I..." questions the KB only partly covers, from general knowledge
    # (docs/eval/Prompt-Experiment-2026-09-19.md, docs/eval/Fix-16-17-Verification-2026-09-19.md).
    # Prompt wording alone did not stop it, so invents_steps() backs rule 5 up in _predict.
    _SYSTEM_PROMPT = (
        "You are a customer support assistant for an online store platform. The "
        "context below comes from the help center for the plan the customer is on, "
        'so anything it says about "your subscription" or "a free subscription" '
        "applies to this customer.\n\n"
        "Answer using ONLY the context. Follow these rules:\n"
        "1. Answer the exact question asked. If the context states a limit or "
        "restriction that applies (for example what a free subscription does or "
        "does not allow), say so plainly - do not give a generic statement that "
        "skips it.\n"
        "2. Never say something is possible unless the context says it is possible "
        "on this customer's plan.\n"
        "3. If the context does not contain the answer, reply only: \"I don't have "
        'information about that in our help center." Do not suggest websites, '
        "contact channels, phone numbers or hours, and do not use general "
        "knowledge.\n"
        "4. Answer in one to three sentences.\n"
        "5. Never describe menu paths, buttons, screens or step-by-step instructions "
        "unless they appear in the context. If the context only says that something "
        'can be done (for example "in your Shopify Payments settings"), say only that '
        "and do not add steps.\n\n"
        "Context:\n{context}"
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

        with log_latency("retrieval", node=type(self).__name__, query=last_user_message) as fields:
            # The retriever interface itself doesn't expose scores - query
            # the underlying vectorstore directly, purely for logging.
            # Tier-leakage rate (docs/eval/Metrics.md #3) is scored from
            # this "source" field: any assets/paid/* source for a free
            # user's turn (or vice versa) is a hard failure.
            try:
                scored = retriever.vectorstore.similarity_search_with_score(last_user_message)
                fields["retrieved_docs"] = [
                    {"source": _relative_source(doc.metadata.get("source")), "score": round(float(score), 4)}
                    for doc, score in scored
                ]
            except Exception:
                fields["retrieved_docs"] = None

            chain = create_retrieval_chain(retriever, self._combine_docs_chain)
            result = chain.invoke({"input": last_user_message})

            answer = result["answer"]
            context = "\n".join(doc.page_content for doc in result["context"])
            fields["invented_steps_blocked"] = invents_steps(answer, context)

        return NOT_COVERED_REPLY if fields["invented_steps_blocked"] else answer


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
