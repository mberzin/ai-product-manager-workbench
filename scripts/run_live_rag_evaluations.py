"""Run two optional live Phase 4 smoke evaluations.

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


def evidence_used(result) -> tuple[list[str], list[str]]:
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
    return tools, knowledge


def main() -> int:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("Live RAG evaluations skipped: OPENAI_API_KEY is unavailable.")
        return 0

    agent = load_agent()
    questions = [
        "Who are CallGuard's primary customer personas and what do they care about? Keep the answer under 250 words.",
        (
            "Given the quantitative evidence and company strategy, should CallGuard prioritize "
            "fixing v3.2 or investing in the explainability feature? Use both retrieval and "
            "analytical tools, cite the evidence used, and keep the answer under 250 words."
        ),
    ]
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
        tools, knowledge = evidence_used(result)
        print(f"Tools used: {', '.join(tools) if tools else 'none'}")
        print(f"Knowledge used: {', '.join(knowledge) if knowledge else 'none'}")
        print(str(result.final_output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
