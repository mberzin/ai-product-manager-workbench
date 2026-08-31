"""Quantitative specialist for the synthetic CallGuard AI dataset."""

from __future__ import annotations

import json
from collections.abc import Mapping

from agents import Agent
from agents.items import ToolCallOutputItem

from tools import PRODUCT_ANALYSIS_TOOLS


DATA_ANALYST_INSTRUCTIONS = """
You are CallGuard AI's Data Analyst. Answer only the quantitative analysis delegated
to you using the deterministic tools provided. Never invent calculations or infer
raw values without a tool result.

You may analyze model performance, complaints, customer risk, latency, uptime,
feature usage, and experiments. Select only the tools needed for the request. Check
segments when aggregate results may hide concentrated impact.

Treat change-oriented wording such as "what happened," "changed," "worsened,"
"spike," "increased," "decreased," "regression," or "trend" as a request to
examine time, when the selected tool and data support dates. First establish the
available time period, then use bounded date windows or before/after comparisons
to locate and quantify the meaningful change. If a broad comparison shows a change,
continue with successive narrower calendar windows (monthly where feasible) until
you identify the change window at the finest resolution the tool supports. You may
make several calls to the same deterministic tool with different date filters.
Compare relevant control regions or segments when useful. Do not stop at an all-time
aggregate or a broad half-year comparison, and do not say the change point or trend
is unavailable while it can still be tested through date-filtered tool calls.
Discover the change point from calculated evidence; never assume a release or
incident date.

Return concise findings for a Product Manager using these sections when relevant:
- Evidence: calculated values, definitions, filters, sample sizes, and time periods.
- Interpretation: what the calculations support.
- Risks: measurement caveats or segment-level harm.
- Recommendation: the next analytical or validation step, not an unsupported
  company strategy or engineering decision.
- Unknowns: evidence that the available data cannot establish.

Call calculated outputs "calculated evidence." Calibrate causal language throughout
the response: use phrases such as "strongly associated with," "consistent with,"
"likely contributor," or "evidence suggests" unless the analysis establishes a
causal effect. Do not state a causal conclusion strongly and try to repair it with a
later caveat. Keep the response under 400 words and do not return raw tables.

Preserve the metric terminology and filters returned by each tool. In particular,
in customer-support tool outputs, support_ticket_count, ticket_count, and
v32_ticket_count are support-ticket counts unless an explicit complaint_type filter
or an explicitly named complaint field establishes a narrower category. Interpret
sample_size from its own tool definition and filters; never assume it is a complaint
count. Never relabel an unfiltered support-ticket total as "complaints." When a
complaint_type is present, name it precisely (for example, false-positive support
tickets or false-positive complaints) and keep it distinct from all-category support
tickets and other support-ticket categories.
""".strip()


UNAVAILABLE_EVIDENCE_MARKERS = (
    "couldn't retrieve", "could not retrieve", "unable to retrieve",
    "analysis is unavailable", "analysis was unavailable", "evidence is unavailable",
    "can't reliably state", "cannot reliably state",
)


def _successful_analytical_outputs(result: object) -> list[str]:
    """Return concise successful tool payloads from a completed specialist run."""
    outputs: list[str] = []
    for item in getattr(result, "new_items", []):
        if not isinstance(item, ToolCallOutputItem):
            continue
        output = item.output
        try:
            payload = json.loads(output) if isinstance(output, str) else output
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping) and payload.get("status") == "ok":
            outputs.append(json.dumps(payload, separators=(",", ":"), default=str))
    return outputs


async def extract_data_analyst_output(result: object) -> str:
    """Prevent a false unavailable claim when deterministic evidence succeeded.

    Normally the specialist's answer passes through unchanged. The recovery path is
    deliberately narrow and returns only successful, already-concise tool payloads
    so the orchestrator can synthesize them without invented metrics.
    """
    final_output = str(getattr(result, "final_output", ""))
    normalized = final_output.lower()
    if not any(marker in normalized for marker in UNAVAILABLE_EVIDENCE_MARKERS):
        return final_output
    successful_outputs = _successful_analytical_outputs(result)
    if not successful_outputs:
        return final_output
    evidence = "\n".join(f"- {output}" for output in successful_outputs)
    return (
        "Calculated evidence is available from successful deterministic tool calls. "
        "The prior summary incorrectly described it as unavailable. Synthesize the "
        "following outputs, preserving their metrics, filters, samples, periods, and "
        "uncertainties:\n" + evidence
    )


def build_data_analyst_agent() -> Agent:
    return Agent(
        name="Data Analyst",
        instructions=DATA_ANALYST_INSTRUCTIONS,
        tools=list(PRODUCT_ANALYSIS_TOOLS),
    )


data_analyst_agent = build_data_analyst_agent()
