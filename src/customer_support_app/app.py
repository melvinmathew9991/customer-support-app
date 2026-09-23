"""Streamlit entrypoint. Run with:

    streamlit run src/customer_support_app/app.py

The conversation is saved after every turn under a session id kept in the page URL
(`?session=<id>`), so a browser refresh or a server restart picks it back up. Whoever holds
the URL can read the conversation; see docs/Persistence-Design.md.
"""
import uuid
from typing import Optional

import streamlit as st

from customer_support_app.agents.support import GreetingNode
from customer_support_app.config import get_settings
from customer_support_app.logging_config import setup_logging
from customer_support_app.pipeline import CustomerSupportPipeline
from customer_support_app.session_store import SessionStore, SessionStoreError
from customer_support_app.ui.graph_renderer import GraphRenderer

setup_logging()

st.title("Support")


def _message_kind(content: str, node: Optional[str]) -> str:
    """Classifies a message for styling, per docs/Design.md §4.

    Uses signals the graph already provides rather than inventing new retry detection
    (docs/Rules.md): an exact match against GreetingNode's own canonical retry copy, and
    the node the message's turn ended at, which marks a ticket confirmation. A live
    message reads that node from the pipeline; a resumed one from the saved message.
    """
    if content in GreetingNode.RETRY_PROMPT:
        return "retry"
    if node == "CallCustomerNode":
        return "ticket"
    return "normal"


def _current_node_name(pipeline: CustomerSupportPipeline) -> str:
    return type(pipeline._current_node).__name__


def _append_message(role: str, content: str, kind: str = "normal") -> None:
    st.session_state.messages.append({"role": role, "content": content, "kind": kind})


def _render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        kind = message.get("kind", "normal")
        if kind == "retry":
            st.warning(message["content"])
        elif kind == "ticket":
            st.success(message["content"])
        else:
            st.markdown(message["content"])


def get_answer(query: str, pipeline):
    """
    Queries the model with a given question and returns the answer.
    """
    res, is_over = pipeline.run(query)
    return res, is_over


@st.cache_resource
def _open_store() -> SessionStore:
    return SessionStore(get_settings().session_db_path)


def _session_id() -> str:
    """The id in the URL, or a new one written into it."""
    session_id = st.query_params.get("session")
    if not session_id:
        session_id = uuid.uuid4().hex
        st.query_params["session"] = session_id
    return session_id


def start_chatbot():
    try:
        store = _open_store()
    except SessionStoreError as error:
        st.error(f"Cannot use the saved-conversation database: {error}")
        st.stop()

    session_id = _session_id()
    tab1, tab2 = st.tabs(["Chat", "Graph"])

    with tab1:
        if "pipeline" not in st.session_state:
            pipeline = CustomerSupportPipeline(store=store, session_id=session_id)
            st.session_state.pipeline = pipeline
            st.session_state.messages = []
            if pipeline.resumed:
                # Sessions saved before replies carried their node have no "node" key, and
                # replay their ticket confirmations as plain text.
                st.session_state.messages = [
                    {**m, "kind": _message_kind(m["content"], m.get("node"))}
                    for m in pipeline.transcript()
                ]
            else:
                res, is_over = pipeline.run("")
                for prompt in res:
                    _append_message(
                        "assistant",
                        prompt.message,
                        _message_kind(prompt.message, _current_node_name(pipeline)),
                    )
        else:
            pipeline = st.session_state.pipeline

        profile = pipeline.current_user_profile
        if profile is not None:
            st.caption(f"{profile.name} · {profile.subscription} plan")

        for message in st.session_state.messages:
            _render_message(message)

    if prompt := st.chat_input("Ask a question...", disabled=pipeline.ended):
        _append_message("user", prompt)
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            responses, is_over = get_answer(
                st.session_state.messages[-1]["content"], pipeline
            )

            for full_response in responses:
                answer = full_response.message
                kind = _message_kind(answer, _current_node_name(pipeline))
                if kind == "retry":
                    message_placeholder.warning(answer)
                elif kind == "ticket":
                    message_placeholder.success(answer)
                else:
                    message_placeholder.markdown(answer)
                _append_message("assistant", answer, kind)

    if pipeline.ended:
        st.info("This conversation has ended.")
        if st.button("Start a new conversation"):
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()

    with tab2:
        st.session_state._graph = GraphRenderer().get(_current_node_name(pipeline))

        st.graphviz_chart(st.session_state._graph, use_container_width=True)


start_chatbot()
