"""User-facing Product Manager Orchestrator for the Phase 5 specialist team."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from agents import Agent

from rag import load_vector_store_id


AGENTS_DIR = Path(__file__).resolve().parent


def _load_builder(filename: str, builder_name: str):
    """Load local agent modules without shadowing the SDK's `agents` package."""
    module_path = AGENTS_DIR / filename
    module_name = f"callguard_{module_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load specialist module at {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, builder_name)


build_data_analyst_agent = _load_builder("data_analyst.py", "build_data_analyst_agent")
build_product_strategist_agent = _load_builder(
    "product_strategist.py", "build_product_strategist_agent"
)
build_technical_pm_agent = _load_builder("technical_pm.py", "build_technical_pm_agent")


PRODUCT_MANAGER_INSTRUCTIONS = """
You are the senior Product Manager Orchestrator for the fictional CallGuard AI
company. You own the final user-facing answer and may consult three specialists as
tools. Specialists receive only the focused task you send them, so include the
question and necessary context in each delegation.

Delegate selectively:
- Consult the Data Analyst for calculated evidence about models, complaints,
  customers, latency, uptime, feature usage, or experiments.
- Consult the Product Strategist for personas, customer priorities, product
  strategy, roadmap, and business tradeoffs.
- Consult the Technical Product Manager for architecture, APIs, model rollout,
  reliability mitigations, operational risk, and engineering tradeoffs.
- Use no specialist for simple general PM guidance that needs neither CallGuard
  evidence nor specialist expertise.

Avoid unnecessary calls. A focused quantitative question normally needs only the
Data Analyst. A focused company/persona question normally needs only the Product
Strategist. Consult multiple specialists only when their distinct evidence materially
changes a consequential recommendation. Never call all specialists by default.

For purely descriptive company or product knowledge—such as personas, target
customers, strategy priorities, or roadmap priorities—normally consult only the
Product Strategist. Do not consult the Data Analyst merely to embellish a retrieved
answer with unrelated metrics. Add quantitative analysis only when the user's actual
question or decision requires calculated evidence. Add the Technical Product Manager
only when architecture, implementation, reliability mitigation, or engineering
tradeoffs are explicitly relevant.

Mandatory evidence gate: before recommending a model rollback, incident mitigation,
or evidence-based product reprioritization, consult the Data Analyst. If the decision
also depends on customer strategy or technical implementation, consult the relevant
additional specialist(s). Do not make a rollback recommendation while saying the
quantitative evidence is unavailable when the Data Analyst can calculate it.

Synthesize findings into one concise PM answer; do not paste specialist responses.
Resolve disagreements where the evidence allows, and explicitly name unresolved
tradeoffs otherwise. Distinguish:
- Calculated evidence from deterministic analysis.
- Retrieved knowledge from allowlisted company documents, naming filenames when
  specialists provide them.
- Hypotheses or interpretations that still require validation.
- Your final recommendation and prioritized next steps.

Never invent metrics, company strategy, architecture, customer facts, or root cause.
Do not claim causality from correlation or release timing alone. Cite the specific
values, sample sizes, periods, segments, and retrieved sources that support the
answer. Keep the final response concise, practical, and PM-oriented.
""".strip()


def build_product_manager_agent(vector_store_id: str | None = None) -> Agent:
    """Build the orchestrator and its three least-privilege specialist tools."""
    configured_id = vector_store_id if vector_store_id is not None else load_vector_store_id()
    data_analyst = build_data_analyst_agent()
    product_strategist = build_product_strategist_agent(configured_id)
    technical_pm = build_technical_pm_agent(configured_id)

    specialist_tools = [
        data_analyst.as_tool(
            tool_name="consult_data_analyst",
            tool_description=(
                "Consult the Data Analyst for deterministic quantitative evidence about model "
                "performance, complaints, customer risk, latency, uptime, feature usage, or "
                "experiments. Always use for evidence-based rollback decisions. For focused "
                "quantitative questions, do not call other specialists unless needed. Do not "
                "use for purely descriptive personas, strategy, target-customer, or roadmap "
                "questions that require no calculated evidence."
            ),
            max_turns=8,
        ),
        product_strategist.as_tool(
            tool_name="consult_product_strategist",
            tool_description=(
                "Consult the Product Strategist for retrieved CallGuard personas, customer "
                "priorities, product strategy, roadmap context, and business tradeoffs. Use "
                "this specialist alone for purely descriptive company and product knowledge "
                "unless the question itself requires quantitative or technical evidence."
            ),
            max_turns=6,
        ),
        technical_pm.as_tool(
            tool_name="consult_technical_pm",
            tool_description=(
                "Consult the Technical Product Manager for documented architecture, API, model "
                "rollout, reliability mitigation, operational risk, and engineering tradeoffs."
            ),
            max_turns=6,
        ),
    ]
    return Agent(
        name="Product Manager Orchestrator",
        instructions=PRODUCT_MANAGER_INSTRUCTIONS,
        tools=specialist_tools,
    )


product_manager_agent = build_product_manager_agent()
