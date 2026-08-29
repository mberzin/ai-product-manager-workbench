"""Run two optional live Phase 5 multi-agent smoke evaluations.

This script makes OpenAI API calls and is intentionally excluded from unittest
discovery. It prints questions, answers, tool names, and retrieved filenames, but
never credentials.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from collections.abc import Mapping
from pathlib import Path

from agents import Runner
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_agent():
    module_path = PROJECT_ROOT / "agents" / "product_manager.py"
    spec = importlib.util.spec_from_file_location("product_manager", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load the agent definition at {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.product_manager_agent


def raw_field(item, name: str):
    raw_item = item.raw_item
    if isinstance(raw_item, Mapping):
        return raw_item.get(name)
    return getattr(raw_item, name, None)


SPECIALIST_AGENT_NAMES = {
    "consult_data_analyst": "Data Analyst",
    "consult_product_strategist": "Product Strategist",
    "consult_technical_pm": "Technical Product Manager",
}


def evidence_used(result) -> tuple[list[str], list[str], list[str]]:
    tools: list[str] = []
    knowledge: list[str] = []
    for item in result.new_items:
        item_type = raw_field(item, "type")
        if item_type == "function_call":
            name = raw_field(item, "name")
            if name and name not in tools:
                tools.append(name)
        elif item_type == "file_search_call":
            for search_result in raw_field(item, "results") or []:
                filename = (
                    search_result.get("filename")
                    if isinstance(search_result, Mapping)
                    else getattr(search_result, "filename", None)
                )
                if filename and filename not in knowledge:
                    knowledge.append(filename)

    # Agent-as-tool summaries do not always expose a specialist's nested file
    # search items in the outer run. Specialists cite exact allowlisted source
    # filenames, so scan only their public output as a transparent fallback.
    from rag import KNOWLEDGE_FILES

    public_text = "\n".join(
        [str(result.final_output)]
        + [str(getattr(item, "output", "")) for item in result.new_items]
    )
    for filename in KNOWLEDGE_FILES:
        if filename in public_text and filename not in knowledge:
            knowledge.append(filename)
    agents = ["Product Manager Orchestrator"]
    agents.extend(SPECIALIST_AGENT_NAMES[name] for name in tools if name in SPECIALIST_AGENT_NAMES)
    return tools, knowledge, list(dict.fromkeys(agents))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("Live RAG evaluations skipped: OPENAI_API_KEY is unavailable.")
        return 0

    agent = load_agent()
    questions = [
        "What happened to EU latency? Use only the specialist analysis needed and keep the answer under 250 words.",
        (
            "Should we roll back v3.2 specifically for Tier 1 carriers, considering customer "
            "strategy and technical mitigation options? Use the specialists that materially "
            "improve the decision, cite evidence, and keep the answer under 350 words."
        ),
    ]
    if "--complex-only" in sys.argv:
        questions = questions[1:]
    for number, question in enumerate(questions, 1):
        print(f"Evaluation {number}: {question}")
        try:
            result = Runner.run_sync(agent, question)
        except Exception as exc:
            message = str(exc)
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                message = message.replace(api_key, "[REDACTED]")
            print(f"Evaluation {number} failed: {type(exc).__name__}: {message}")
            return 1
        tools, knowledge, agents = evidence_used(result)
        print(f"Agents involved: {' -> '.join(agents)}")
        print(f"Tools used: {', '.join(tools) if tools else 'none'}")
        print(f"Knowledge used: {', '.join(knowledge) if knowledge else 'none'}")
        print(str(result.final_output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
