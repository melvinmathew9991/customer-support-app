"""Streamlit entrypoint. Run with:

    streamlit run src/customer_support_app/app.py
"""
import streamlit as st

from customer_support_app.logging_config import setup_logging
from customer_support_app.pipeline import CustomerSupportPipeline
from customer_support_app.ui.graph_renderer import GraphRenderer

setup_logging()

st.title("Hi, I'm your Shopify Agent")


def get_answer(query: str, pipeline):
    """
    Queries the model with a given question and returns the answer.
    """
    res, is_over = pipeline.run(query)
    return res, is_over


def start_chatbot():
    tab1, tab2 = st.tabs(["Chat", "Graph"])

    with tab1:
        if "messages" not in st.session_state:
            st.session_state.messages = []

        if "pipeline" not in st.session_state:
            pipeline = CustomerSupportPipeline()
            st.session_state.pipeline = pipeline
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

    if prompt := st.chat_input("What is Up?"):
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

    with tab2:
        st.session_state._graph = GraphRenderer().get(
            type(pipeline._current_node).__name__
        )

        st.graphviz_chart(st.session_state._graph, use_container_width=True)


start_chatbot()
