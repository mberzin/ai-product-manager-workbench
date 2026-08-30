"""Streamlit entry point for the AI Product Manager Workbench."""

import importlib.util
import logging
import os
import time
from collections.abc import Mapping
from pathlib import Path

import streamlit as st
from agents import Runner
from dotenv import load_dotenv
from demo_config import (
    bounded_history,
    load_demo_limits,
    request_limit_reached,
    validate_prompt,
)
from rag import KNOWLEDGE_FILES


LOGGER = logging.getLogger(__name__)

SPECIALIST_AGENT_NAMES = {
    "consult_data_analyst": "Data Analyst",
    "consult_product_strategist": "Product Strategist",
    "consult_technical_pm": "Technical Product Manager",
}

DEMO_QUESTIONS = (
    ("EU latency diagnosis", "What happened to EU latency?", False),
    (
        "Customer personas",
        "Who are CallGuard's main personas and what matters most to them?",
        False,
    ),
    (
        "Featured · Tier 1 rollback",
        "Should we roll back v3.2 specifically for Tier 1 carriers? Consider model "
        "performance, customer strategy, and technical mitigation options.",
        True,
    ),
    (
        "Product prioritization",
        "Should CallGuard prioritize fixing v3.2 or investing further in explainability?",
        False,
    ),
)


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
    # Nested specialist runs return concise text to the orchestrator rather than
    # exposing their internal run items. Specialists are instructed to name source
    # files, so recover those public citations from their outputs and the synthesis.
    public_outputs = [str(result.final_output)]
    public_outputs.extend(str(item.output) for item in result.new_items if hasattr(item, "output"))
    combined_output = "\n".join(public_outputs)
    for filename in KNOWLEDGE_FILES:
        if filename in combined_output and filename not in filenames:
            filenames.append(filename)
    return filenames


def agents_involved_in_run(result) -> list[str]:
    """Return public agent names from delegation calls, without hidden reasoning."""
    names = ["Product Manager Orchestrator"]
    for tool_name in tools_used_in_run(result):
        agent_name = SPECIALIST_AGENT_NAMES.get(tool_name)
        if agent_name and agent_name not in names:
            names.append(agent_name)
    return names


def execution_metadata(result, latency_seconds: float) -> dict:
    """Return safe, public execution metrics exposed by the SDK."""
    metadata = {"Response latency": f"{max(0.0, latency_seconds):.2f} seconds"}
    wrapper = getattr(result, "context_wrapper", None)
    usage = getattr(wrapper, "usage", None)
    if usage is not None and getattr(usage, "total_tokens", 0):
        metadata.update({
            "Model requests": int(getattr(usage, "requests", 0) or 0),
            "Input tokens": int(getattr(usage, "input_tokens", 0) or 0),
            "Output tokens": int(getattr(usage, "output_tokens", 0) or 0),
            "Total tokens": int(getattr(usage, "total_tokens", 0) or 0),
        })
    return metadata


def show_execution_metadata(metadata: dict) -> None:
    """Display metrics without prompts, private traces, or chain-of-thought."""
    with st.expander("Execution metadata"):
        for label, value in metadata.items():
            st.write(f"{label}: {value}")


# Load local environment variables without reading, printing, or displaying them.
load_dotenv()

st.set_page_config(
    page_title="AI Product Manager Workbench",
    page_icon=":material/explore:",
    layout="centered",
)


def configure_api_key_from_streamlit_secrets() -> None:
    """Use a deployment secret when no environment-based key is configured."""
    if os.getenv("OPENAI_API_KEY"):
        return
    try:
        api_key = st.secrets.get("OPENAI_API_KEY")
    except (FileNotFoundError, KeyError):
        api_key = None
    if api_key:
        os.environ["OPENAI_API_KEY"] = str(api_key)


configure_api_key_from_streamlit_secrets()
product_manager_agent = load_product_manager_agent()
limits = load_demo_limits()

st.title("AI Product Manager Workbench")
st.markdown("#### Agentic product decision support over a synthetic B2B AI product.")
st.info(
    "**Demo environment — all company, customer, and product data are synthetic.**",
    icon=":material/science:",
)
st.write(
    "The workbench combines specialized AI agents, deterministic analytics, "
    "company knowledge retrieval, and evidence-grounded recommendations."
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "request_count" not in st.session_state:
    st.session_state.request_count = 0

limit_reached = request_limit_reached(st.session_state.request_count, limits)

st.subheader("Try an example")
st.caption("Choose a scenario to submit it. The featured question exercises the full system.")
selected_question = None
question_columns = st.columns(2)
for index, (label, question, featured) in enumerate(DEMO_QUESTIONS):
    with question_columns[index % 2]:
        if st.button(
            label,
            key=f"demo_question_{index}",
            type="primary" if featured else "secondary",
            icon=":material/stars:" if featured else None,
            disabled=limit_reached,
            width="stretch",
        ):
            selected_question = question

with st.expander("About this project"):
    st.markdown(
        """
CallGuard AI is a fictional company and every record in this demo is synthetic.
This portfolio project explores how an AI Product Manager can combine repeatable
calculations with company context to support—not replace—human product judgment.

- **Deterministic tools** calculate auditable metrics from allowlisted CSV files.
- **RAG** retrieves qualitative context from five allowlisted knowledge documents.
- **Specialists** separate quantitative, strategic, and technical responsibilities.
- **Evaluation** measures routing, evidence, latency, and variability on synthetic cases.

This is a learning system, not production decision automation. It has no live
customer data, authentication, durable memory, or guarantee of consistent model
synthesis. Validate recommendations before acting on them.
"""
    )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("agents"):
            with st.expander("Agents involved"):
                st.write(" → ".join(message["agents"]))
        if message.get("tools"):
            with st.expander("Tools used"):
                st.write(", ".join(message["tools"]))
        if message.get("knowledge"):
            with st.expander("Knowledge used"):
                st.write(", ".join(message["knowledge"]))
        if message.get("execution"):
            show_execution_metadata(message["execution"])

if limit_reached:
    st.warning(
        "This demo session has reached its request limit. Refresh the page to start "
        "a new session, or run the project locally for continued exploration."
    )

typed_question = st.chat_input(
    "Ask a product question...",
    key="product_problem_input",
    max_chars=limits.max_prompt_chars,
    disabled=limit_reached,
    submit_mode="disable",
)
product_problem = selected_question or typed_question

if product_problem:
    validation_error = validate_prompt(product_problem, limits)
    if validation_error:
        st.warning(validation_error)
        st.stop()

    st.session_state.request_count += 1
    st.session_state.messages.append({"role": "user", "content": product_problem})
    st.session_state.messages = bounded_history(
        st.session_state.messages, limits.max_history_messages
    )
    with st.chat_message("user"):
        st.markdown(product_problem)

    with st.chat_message("assistant"):
        tools_used = []
        knowledge_used = []
        agents_involved = []
        execution = {}
        if not os.getenv("OPENAI_API_KEY"):
            response = (
                "`OPENAI_API_KEY` is not configured. Add it to your local `.env` "
                "file, then restart Streamlit."
            )
            st.error(response)
        else:
            try:
                with st.status(
                    "Analyzing request...",
                    expanded=True,
                ) as run_status:
                    st.write(
                        "The orchestrator is selecting relevant specialists and evidence. "
                        "Complex requests typically take 15–20 seconds."
                    )
                    # Keep UI-only metadata out of the model's conversation input.
                    conversation = [
                        {"role": message["role"], "content": message["content"]}
                        for message in st.session_state.messages
                    ]
                    started_at = time.perf_counter()
                    result = Runner.run_sync(
                        product_manager_agent,
                        conversation,
                    )
                    latency_seconds = time.perf_counter() - started_at
                    run_status.update(
                        label="Recommendation ready",
                        state="complete",
                        expanded=False,
                    )
                response = str(result.final_output)
                tools_used = tools_used_in_run(result)
                knowledge_used = knowledge_used_in_run(result)
                agents_involved = agents_involved_in_run(result)
                execution = execution_metadata(result, latency_seconds)
                st.markdown(response)
                if agents_involved:
                    with st.expander("Agents involved"):
                        st.write(" → ".join(agents_involved))
                if tools_used:
                    with st.expander("Tools used"):
                        st.write(", ".join(tools_used))
                if knowledge_used:
                    with st.expander("Knowledge used"):
                        st.write(", ".join(knowledge_used))
                show_execution_metadata(execution)
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
            "agents": agents_involved,
            "execution": execution,
        }
    )
    st.session_state.messages = bounded_history(
        st.session_state.messages, limits.max_history_messages
    )
