import abc
import logging
import re
from pathlib import Path
from typing import List, Optional, Type

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel

from customer_support_app.config import PROJECT_ROOT, get_settings
from customer_support_app.domain.chat import MessageHistory, Role
from customer_support_app.graph.edge import BaseEdge
from customer_support_app.graph.node import BaseNode
from customer_support_app.logging_config import log_latency

logger = logging.getLogger(__name__)

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
    # Plain-prose steps ("by going to the app and selecting Settings") and pointers to
    # instructions the knowledge base does not have (#17).
    re.compile(r"\bgo(?:es|ing)?\s+to\s+(?:the|your)\b", re.I),
    re.compile(r"\bselect(?:s|ed|ing)?\b", re.I),
    re.compile(r"\bopen(?:s|ing)?\s+(?:the|your)\b", re.I),
    re.compile(r"\binstructions?\b", re.I),
    re.compile(r"\bdownload\w*", re.I),
)


def invents_steps(answer: str, context: str) -> bool:
    """True if the answer gives UI navigation the retrieved context never uses."""
    return any(m.search(answer) and not m.search(context) for m in _NAVIGATION_MARKERS)


# Where in the product something is done: "in your store admin", "through the online form",
# "using the shipping labels feature".
_PLACE = re.compile(
    r"\b(?:in|through|from|via|under|using)\s+(?:the|your|their|our)\s+"
    r"(?:[\w'-]+\s+){0,4}?"
    r"(?:settings|admin|app|area|section|page|menu|dashboard|screen|tab|form|portal|feature"
    r"|tool|option|button)\b",
    re.I,
)
_PREPOSITION = re.compile(r"^\w+\s+")
# "your online form", "their online form" and "Brightstall's online form" name the same place.
_DETERMINER = re.compile(r"\b(?:the|your|their|our|its|brightstall's)\b")
_WORD = re.compile(r"[a-z0-9]+")
# Words that say nothing about which task a question is about, including the product names.
_NOT_TASK_WORDS = {
    "a", "about", "an", "and", "are", "brightstall", "can", "do", "does", "for", "from", "get",
    "how", "i", "i'll", "if", "in", "is", "it", "me", "my", "of", "on", "or", "pos", "should",
    "the", "to", "what", "when", "where", "which", "who", "why", "will", "with", "would", "you",
    "your",
}


def _normalized(text: str) -> str:
    return _DETERMINER.sub("<d>", " ".join(text.lower().replace("’", "'").split()))


def _stems(text: str) -> set:
    # A 5-letter prefix is enough to match "respond"/"response" or "payout"/"payouts".
    return {w[:5] for w in _WORD.findall(text.lower()) if w not in _NOT_TASK_WORDS}


def names_unsupported_place(answer: str, context: str, question: str) -> bool:
    """True if the answer says where to do something, and no context sentence says it for
    this task: one that contains the same place and also mentions what the question asks.

    Splicing is how the 3B model invents a location from real text: "check your pay period
    in your Brightstall Payments settings" joins the pay-period sentence to the place named
    in the bank-details sentence, and "reset your password in your store admin" borrows a
    place from the compliance text (#17). Heuristic, like invents_steps().
    """
    context_sentences = [_normalized(s) for s in re.split(r"(?<=[.!?])\s+|\n+", context)]
    for match in _PLACE.finditer(answer):
        place = _normalized(_PREPOSITION.sub("", match.group(0)))
        task = _stems(question) - _stems(place)
        if not any(place in s and (not task or task & _stems(s)) for s in context_sentences):
            return True
    return False


_TOKEN = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_NEGATIONS = {
    "not", "no", "never", "cannot", "can't", "don't", "doesn't", "isn't", "aren't", "won't",
}
# What a plan does or does not let a merchant do: "you do not need any POS hardware", "a free
# subscription does not include selling in person". Matched by their first four letters.
_CLAIM_VERBS = {"need", "incl", "allo", "sell", "add", "addi", "adds", "acce", "buy", "buyi",
                "coun", "spli", "offe"}
_NOT_OBJECT_WORDS = _NOT_TASK_WORDS | {"any", "this", "that", "plan", "subscription", "toward",
                                       "towards", "only", "also", "more", "than"}


def _claims(text: str, whole_sentence: bool = False) -> list:
    """(verb, object words, negated) for each claim verb in the text.

    A claim is negated by a negation in the three words before it or, with whole_sentence,
    anywhere in its sentence ("selling in person is not included").
    """
    if whole_sentence:
        return [c for s in _SENTENCE_SPLIT.split(text) for c in _sentence_claims(s)]
    return _sentence_claims(text, whole_sentence=False)


def _sentence_claims(text: str, whole_sentence: bool = True) -> list:
    tokens = _TOKEN.findall(text.lower().replace("’", "'"))
    sentence_negated = whole_sentence and any(t in _NEGATIONS for t in tokens)
    claims = []
    for i, token in enumerate(tokens):
        if token[:4] not in _CLAIM_VERBS:
            continue
        negated = sentence_negated or any(t in _NEGATIONS for t in tokens[max(0, i - 3):i])
        objects = {t[:5] for t in tokens[i + 1:i + 6]
                   if t not in _NOT_OBJECT_WORDS and t[:4] not in _CLAIM_VERBS}
        claims.append((token[:4], objects, negated))
    return claims


def _conflicts(affirmed: list, negated_claims: list) -> bool:
    return any(
        v == nv and objs & nobjs
        for v, objs, neg in affirmed if not neg
        for nv, nobjs, nneg in negated_claims if nneg
    )


def contradicted_restriction(answer: str, context: str) -> Optional[str]:
    """The context's own words, if the answer affirms something the context rules out.

    The 3B model sometimes turns a stated restriction around: asked what POS hardware a
    free-plan store should buy, it answered "You need to buy Brightstall POS hardware" where
    the context says "you do not need any Brightstall POS hardware on this plan" (#5). Such an
    answer is replaced by the restriction itself, which is covered and exact. Heuristic: a
    claim verb (need, include, allow, sell, add, accept, buy, count, split, offer) that the
    answer uses without negation and a context sentence uses with it, about the same thing.
    """
    answer_claims = _claims(answer, whole_sentence=True)
    conflicting = [s.strip() for s in _SENTENCE_SPLIT.split(context)
                   if _conflicts(answer_claims, _claims(s))]
    return " ".join(dict.fromkeys(conflicting[:2])) or None


_YES_LEAD = re.compile(r"^\s*yes\b[,.!]?\s*", re.I)
_YES_NO_QUESTION = re.compile(r"^\s*(?:do|does|is|are|can|could|will|would|should|am)\b", re.I)


def drop_contradicted_yes(answer: str, question: str) -> str:
    """The answer without a leading "Yes" that the answer itself goes on to deny.

    "Does an app that fulfills my orders count toward my location limit?" was answered "Yes,
    an app ... is treated as a location, but it does not count toward the location limit":
    the rest is right, the "Yes" answers the opposite question (#5).
    """
    if not (_YES_NO_QUESTION.search(question) and _YES_LEAD.search(answer)):
        return answer
    asked = [(v, objs, False) for v, objs, _neg in _claims(question)]
    if not _conflicts(asked, _claims(answer)):
        return answer
    rest = _YES_LEAD.sub("", answer, count=1)
    return rest[:1].upper() + rest[1:]


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
    # Prompt wording alone did not stop it, so invents_steps() and names_unsupported_place()
    # back rule 5 up in _predict, and contradicted_restriction() backs up rules 1 and 2. A
    # prompt rule for plan restrictions was tried and made things worse: the 3B model then
    # told paid customers their plan did not include things it does.
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
        'can be done (for example "in your Brightstall Payments settings"), say only that '
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
                    {
                        "source": _relative_source(doc.metadata.get("source")),
                        "score": round(float(score), 4),
                    }
                    for doc, score in scored
                ]
            except Exception:
                # Logging-only lookup: the answer does not depend on it, but the eval
                # scores recall and tier leakage from this field, so a failure here
                # must be visible rather than silently blinding both metrics.
                logger.warning(
                    "Could not log the retrieved documents for this turn; recall and "
                    "tier-leakage scoring will not see it",
                    exc_info=True,
                )
                fields["retrieved_docs"] = None

            chain = create_retrieval_chain(retriever, self._combine_docs_chain)
            result = chain.invoke({"input": last_user_message})

            answer = result["answer"]
            context = "\n".join(doc.page_content for doc in result["context"])
            fields["invented_steps_blocked"] = invents_steps(answer, context)
            fields["unsupported_place_blocked"] = names_unsupported_place(
                answer, context, last_user_message
            )

            restriction = contradicted_restriction(answer, context)
            fields["contradicted_restriction_replaced"] = restriction is not None

        if fields["invented_steps_blocked"] or fields["unsupported_place_blocked"]:
            return NOT_COVERED_REPLY
        if restriction is not None:
            return restriction
        return drop_contradicted_yes(answer, last_user_message)


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
