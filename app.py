"""Streamlit entry point for the AI Product Manager Workbench."""

import importlib.util
import logging
import os
from pathlib import Path

import streamlit as st
from agents import Runner
from dotenv import load_dotenv


LOGGER = logging.getLogger(__name__)


def load_product_manager_agent():
    """Load our local agent definition without shadowing the SDK's `agents` package."""
    module_path = Path(__file__).parent / "agents" / "product_manager.py"
    spec = importlib.util.spec_from_file_location("product_manager", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load the agent definition at {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.product_manager_agent


# Load local environment variables without reading, printing, or displaying them.
load_dotenv()
product_manager_agent = load_product_manager_agent()

st.set_page_config(page_title="AI Product Manager Workbench", page_icon="🧭")
st.title("AI Product Manager Workbench")
st.caption("Phase 1 — explore an ambiguous product problem with a senior AI PM.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

product_problem = st.chat_input("Describe a product problem...")

if product_problem:
    st.session_state.messages.append({"role": "user", "content": product_problem})
    with st.chat_message("user"):
        st.markdown(product_problem)

    with st.chat_message("assistant"):
        if not os.getenv("OPENAI_API_KEY"):
            response = (
                "`OPENAI_API_KEY` is not configured. Add it to your local `.env` "
                "file, then restart Streamlit."
            )
            st.error(response)
        else:
            try:
                with st.spinner("Analyzing the product problem..."):
                    # Passing the message list gives the agent the visible chat history.
                    result = Runner.run_sync(
                        product_manager_agent,
                        st.session_state.messages,
                    )
                response = str(result.final_output)
                st.markdown(response)
            except Exception as exc:
                # Log useful diagnostics while defensively redacting the API key.
                exception_message = str(exc)
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    exception_message = exception_message.replace(api_key, "[REDACTED]")
                LOGGER.error(
                    "Agent/API call failed (%s): %s",
                    type(exc).__name__,
                    exception_message,
                )

                # Keep the message shown in the UI generic and safe.
                response = (
                    "The agent could not complete this request. Check your API key, "
                    "network connection, and terminal output, then try again."
                )
                st.error(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
