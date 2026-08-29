"""Streamlit entry point for the AI Product Manager Workbench."""

import importlib.util
import logging
import os
from collections.abc import Mapping
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


def tools_used_in_run(result) -> list[str]:
    """Extract local function-tool names from SDK run metadata for UI disclosure."""
    names: list[str] = []
    for item in result.new_items:
        raw_item = item.raw_item
        if isinstance(raw_item, Mapping):
            item_type = raw_item.get("type")
            name = raw_item.get("name")
        else:
            item_type = getattr(raw_item, "type", None)
            name = getattr(raw_item, "name", None)
        if item_type == "function_call" and name and name not in names:
            names.append(name)
    return names


def knowledge_used_in_run(result) -> list[str]:
    """Extract retrieved source filenames from included file-search results."""
    filenames: list[str] = []
    for item in result.new_items:
        raw_item = item.raw_item
        if isinstance(raw_item, Mapping):
            item_type = raw_item.get("type")
            results = raw_item.get("results") or []
        else:
            item_type = getattr(raw_item, "type", None)
            results = getattr(raw_item, "results", None) or []
        if item_type != "file_search_call":
            continue
        for search_result in results:
            if isinstance(search_result, Mapping):
                filename = search_result.get("filename")
            else:
                filename = getattr(search_result, "filename", None)
            if filename and filename not in filenames:
                filenames.append(filename)
    return filenames


# Load local environment variables without reading, printing, or displaying them.
load_dotenv()
product_manager_agent = load_product_manager_agent()

st.set_page_config(page_title="AI Product Manager Workbench", page_icon="🧭")
st.title("AI Product Manager Workbench")
st.caption("Phase 4 — combine product judgment, calculated evidence, and retrieved company context.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("tools"):
            with st.expander("Tools used"):
                st.write(", ".join(message["tools"]))
        if message.get("knowledge"):
            with st.expander("Knowledge used"):
                st.write(", ".join(message["knowledge"]))

product_problem = st.chat_input("Describe a product problem...")

if product_problem:
    st.session_state.messages.append({"role": "user", "content": product_problem})
    with st.chat_message("user"):
        st.markdown(product_problem)

    with st.chat_message("assistant"):
        tools_used = []
        knowledge_used = []
        if not os.getenv("OPENAI_API_KEY"):
            response = (
                "`OPENAI_API_KEY` is not configured. Add it to your local `.env` "
                "file, then restart Streamlit."
            )
            st.error(response)
        else:
            try:
                with st.spinner("Analyzing the product problem..."):
                    # Keep UI-only metadata out of the model's conversation input.
                    conversation = [
                        {"role": message["role"], "content": message["content"]}
                        for message in st.session_state.messages
                    ]
                    result = Runner.run_sync(
                        product_manager_agent,
                        conversation,
                    )
                response = str(result.final_output)
                tools_used = tools_used_in_run(result)
                knowledge_used = knowledge_used_in_run(result)
                st.markdown(response)
                if tools_used:
                    with st.expander("Tools used"):
                        st.write(", ".join(tools_used))
                if knowledge_used:
                    with st.expander("Knowledge used"):
                        st.write(", ".join(knowledge_used))
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

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response,
            "tools": tools_used,
            "knowledge": knowledge_used,
        }
    )
