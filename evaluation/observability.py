"""SDK hooks and public run metadata used by evaluation and UI observability."""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from agents.lifecycle import RunHooksBase
from rag import KNOWLEDGE_FILES


SPECIALIST_TOOL_TO_NAME = {
    "consult_data_analyst": "Data Analyst",
    "consult_product_strategist": "Product Strategist",
    "consult_technical_pm": "Technical Product Manager",
}

TOOL_FAMILIES = {
    "compare_model_versions": "model_performance",
    "calculate_precision": "model_performance",
    "calculate_recall": "model_performance",
    "calculate_false_positive_rate": "model_performance",
    "segment_model_performance": "model_performance",
    "analyze_complaint_trends": "complaints",
    "segment_complaints": "complaints",
    "identify_high_risk_customers": "customer_risk",
    "analyze_latency_by_region": "latency",
    "analyze_uptime_by_customer": "reliability",
    "analyze_feature_usage": "feature_usage",
    "analyze_experiment": "experiments",
    "compare_experiment_segments": "experiments",
}


@dataclass
class ToolEvent:
    agent: str
    tool: str
    family: str
    started_at: float
    duration_seconds: float | None = None
    success: bool = False


class EvaluationHooks(RunHooksBase):
    """Capture public lifecycle metadata without prompts or chain-of-thought."""

    def __init__(self) -> None:
        self.agent_starts: list[str] = []
        self.tool_events: list[ToolEvent] = []
        self._active: dict[tuple[str, str], list[ToolEvent]] = {}

    async def on_agent_start(self, context, agent) -> None:
        if agent.name not in self.agent_starts:
            self.agent_starts.append(agent.name)

    async def on_tool_start(self, context, agent, tool) -> None:
        family = TOOL_FAMILIES.get(tool.name, "specialist_delegation")
        event = ToolEvent(agent=agent.name, tool=tool.name, family=family,
                          started_at=time.perf_counter())
        self.tool_events.append(event)
        self._active.setdefault((agent.name, tool.name), []).append(event)

    async def on_tool_end(self, context, agent, tool, result) -> None:
        active = self._active.get((agent.name, tool.name), [])
        if active:
            event = active.pop(0)
            event.duration_seconds = max(0.0, time.perf_counter() - event.started_at)
            event.success = True

    def snapshot(self) -> dict[str, Any]:
        events = [asdict(event) for event in self.tool_events]
        return {
            "agents_started": list(self.agent_starts),
            "tool_events": events,
            "successful_tool_calls": sum(event.success for event in self.tool_events),
            "failed_tool_calls": sum(not event.success for event in self.tool_events),
        }


def usage_metadata(result: object) -> dict[str, int] | None:
    """Return actual SDK usage totals, or None when a provider omits usage."""
    wrapper = getattr(result, "context_wrapper", None)
    usage = getattr(wrapper, "usage", None)
    if usage is None:
        return None
    values = {
        "requests": int(getattr(usage, "requests", 0) or 0),
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }
    return values if any(values.values()) else None


def cited_knowledge(result: object) -> list[str]:
    """Find exact allowlisted filenames in public outputs, never hidden reasoning."""
    items = getattr(result, "new_items", [])
    public_text = "\n".join(
        [str(getattr(result, "final_output", ""))]
        + [str(getattr(item, "output", "")) for item in items]
    )
    return [filename for filename in KNOWLEDGE_FILES if filename in public_text]


def specialist_names_from_events(events: list[dict[str, Any]]) -> list[str]:
    names = []
    for event in events:
        name = SPECIALIST_TOOL_TO_NAME.get(event["tool"])
        if name and name not in names:
            names.append(name)
    return names
