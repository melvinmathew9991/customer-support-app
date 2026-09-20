"""Streamlit entrypoint. Run with:

    streamlit run src/customer_support_app/app.py

The conversation is saved after every turn under a session id kept in the page URL
(`?session=<id>`), so a browser refresh or a server restart picks it back up. Whoever holds
the URL can read the conversation; see docs/Persistence-Design.md.
"""
import uuid

import streamlit as st

from customer_support_app.config import get_settings
from customer_support_app.logging_config import setup_logging
from customer_support_app.pipeline import CustomerSupportPipeline
from customer_support_app.session_store import SessionStore, SessionStoreError
from customer_support_app.ui.graph_renderer import GraphRenderer

setup_logging()

st.title("Hi, I'm your Shopify Agent")


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
                st.session_state.messages = pipeline.transcript()
            else:
                res, is_over = pipeline.run("")
                for prompt in res:
                    st.session_state.messages.append(
                        {"role": "assistant", "content": prompt.message}
                    )
        else:
            pipeline = st.session_state.pipeline

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input("What is Up?", disabled=pipeline.ended):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            responses, is_over = get_answer(
                st.session_state.messages[-1]["content"], pipeline
            )

            for full_response in responses:
                answer = full_response.message
                message_placeholder.markdown(answer)
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )

    if pipeline.ended:
        st.info("This conversation has ended.")
        if st.button("Start a new conversation"):
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()

    with tab2:
        st.session_state._graph = GraphRenderer().get(
            type(pipeline._current_node).__name__
        )

        st.graphviz_chart(st.session_state._graph, use_container_width=True)


start_chatbot()
